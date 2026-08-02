"""Micro-suite fixtures: the 1k fabric's operator/engine/gate surfaces.

Everything is constructed through factory/registry paths with parameters
from ``perf/synth/artifacts/`` (No-Hardcoding Rule, CLAUDE.md §6.4). The
session-scoped ``fabric_1k`` fixture comes from ``perf/conftest.py``
(11-02); the fixtures here derive the operator registry, projection engine,
and gate environment from it once per session so benchmark rounds measure
only the operation under test.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, NamedTuple

import pytest

from perf.suites.common import (
    PerfPlan,
    build_operator_registry,
    instant,
    load_artifact,
)

if TYPE_CHECKING:
    from ccf.boot import FabricHandle
    from ccf.operators.registry import OperatorRegistry
    from ccf.projection.engine import ProjectionEngine


@pytest.fixture(scope="session")
def control() -> Any:
    return load_artifact("controlplane.yaml")


@pytest.fixture(scope="session")
def ontology() -> Any:
    return load_artifact("ontology.yaml")


@pytest.fixture(scope="session")
def tenant_id(ontology: Any) -> str:
    return str(ontology["tenant_id"])


@pytest.fixture(scope="session")
def boundary(control: Any) -> datetime:
    return instant(control["decision"]["temporal_boundary"])


@pytest.fixture(scope="session")
def decision_now(control: Any) -> datetime:
    return instant(control["decision"]["now"])


class OperatorEnv(NamedTuple):
    """The 1k fabric's operator surface, built once per session."""

    operators: "OperatorRegistry"
    policy_version: str


@pytest.fixture(scope="session")
def operator_env(
    fabric_1k: "FabricHandle", control: Any, ontology: Any
) -> OperatorEnv:
    operators, policy_version = build_operator_registry(
        reader=fabric_1k.reader,
        registry=fabric_1k.registry,
        control=control,
        ontology=ontology,
    )
    return OperatorEnv(operators=operators, policy_version=policy_version)


@pytest.fixture(scope="session")
def graph_view(
    fabric_1k: "FabricHandle", tenant_id: str, boundary: datetime
) -> Any:
    return fabric_1k.reader.as_of(tenant_id=tenant_id, at=boundary)


@pytest.fixture(scope="session")
def engine(
    fabric_1k: "FabricHandle", operator_env: OperatorEnv
) -> "ProjectionEngine":
    from ccf.projection.engine import ProjectionEngine

    return ProjectionEngine(
        reader=fabric_1k.reader, registry=operator_env.operators
    )


@pytest.fixture(scope="session")
def full_plan(control: Any, operator_env: OperatorEnv) -> PerfPlan:
    return PerfPlan(
        plan_id=control["product_class"]["plan_id"],
        required=operator_env.operators.keys(),
    )


@pytest.fixture(scope="session")
def perspective(control: Any) -> Any:
    from ccf.projection.plan import Perspective

    return Perspective(
        principal_id=control["perspective"]["principal_id"],
        role=control["perspective"]["role"],
    )
