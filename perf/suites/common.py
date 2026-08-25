"""Shared construction helpers for the perf suites (PERF-01/PERF-02).

Everything here mirrors the deployment-code shapes the examples establish:
operators are constructed from the declared parameter sets in
``perf/synth/artifacts/controlplane.yaml`` (D-IMPL-38; No-Hardcoding Rule,
CLAUDE.md §6.4), the projection plan is thin deployment code, and nothing
reads a clock — the decision instants come from the artifact (D-08).

No timing judgment lives here or anywhere in ``perf/suites/`` — thresholds
and verdicts belong to ``perf/gate.py`` alone (D-02).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import yaml

from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.operators.categories import (
    PolicyFilter,
    PolicyFilterParameters,
    SimilaritySelect,
    SimilaritySelectParameters,
    TemporalAsOf,
    TemporalAsOfParameters,
    TraversalNeighborhood,
    TraversalNeighborhoodParameters,
)
from ccf.operators.registry import OperatorRegistry
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.similarity.protocol import TokenOverlapIndex

from perf.conftest import ARTIFACTS


def load_artifact(name: str) -> Any:
    """Load one of the perf battery's definition artifacts (D-09)."""
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def instant(value: object) -> datetime:
    """Attach UTC at the artifact boundary (PyYAML yields naive datetimes)."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class PerfPlan:
    """The perf battery's Π — thin deployment code, values from artifacts.

    Declares which operators its interpretation depends on and interprets
    their output; it does not run them (the L6 lineage gate compares the
    engine's independent record). The payload is deliberately small so the
    scale curves measure operator + projection mechanism, not payload
    serialization.
    """

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "entity_count": len(view.entities),
                "relationship_count": len(view.relationships),
            },
        )


class PerfPanelPlan:
    """The replay suite's Π — thin, like every projection.

    Differs from :class:`PerfPlan` only in its payload shape (relationship
    TYPES rather than a count); kept as a second plan class so the replay
    record's byte-exact reproduction assert has a distinct, stable payload.
    """

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "entity_count": len(view.entities),
                "relationship_types": sorted(
                    {edge.claim.relationship_type for edge in view.relationships}
                ),
            },
        )


def build_operator_registry(
    *,
    reader: Any,
    registry: ControlPlaneProtocol,
    control: Any,
    ontology: Any,
) -> tuple[OperatorRegistry, str]:
    """Register the four canonical operators from the declared parameters.

    Mirrors the registration shape of ``archive/examples/04-cross-process`` — every
    parameter value comes from ``controlplane.yaml``/``ontology.yaml``; the
    similarity corpus is read off the booted fabric's graph view at the
    artifact-declared boundary.

    Returns the populated :class:`OperatorRegistry` plus the policy-bundle
    version the fabric was booted with (needed for ``PolicyFilter`` and for
    product lineage).
    """
    keys = control["keys"]
    policy_version, _ = registry.resolve_latest(keys["policy_bundle"])
    operators = build_operators(
        reader=reader,
        control=control,
        ontology=ontology,
        policy_version=policy_version,
    )
    return operators, policy_version


def build_operators(
    *,
    reader: Any,
    control: Any,
    ontology: Any,
    policy_version: str,
) -> OperatorRegistry:
    """The four-category chain from the perf artifacts, given an explicit
    policy-bundle version.

    The single source of operator parameter wiring for every perf suite —
    micro/scale go through :func:`build_operator_registry` (which resolves
    the version off the booted Control Plane), while the replay suite's
    record phase and replay environment call this directly with the version
    they computed (example 06 discipline: same declared parameters → same
    parameter hashes → the recorded step sequence reproduces).
    """
    params = control["operator_parameters"]
    boundary = instant(control["decision"]["temporal_boundary"])
    tenant_id: str = ontology["tenant_id"]

    operators = OperatorRegistry()
    operators.register(
        PolicyFilter(
            parameters=PolicyFilterParameters(
                permitted_policy_bundle_versions=frozenset({policy_version}),
                classification_attribute_by_class=dict(
                    ontology["classification_attribute_by_class"]
                ),
                permitted_classifications=frozenset(
                    params["policy"]["permitted_classifications"]
                ),
            )
        )
    )
    corpus_attribute = ontology["similarity_corpus_attribute_by_class"]
    view = reader.as_of(tenant_id=tenant_id, at=boundary)
    corpus = {
        (tenant_id, record.claim.entity_uri): record.claim.attributes[
            corpus_attribute[record.claim.entity_class]
        ]
        for record in view.entities
        if record.claim.entity_class in corpus_attribute
    }
    operators.register(
        SimilaritySelect(
            parameters=SimilaritySelectParameters(
                query=params["similarity"]["query"],
                minimum_score_percent=params["similarity"][
                    "minimum_score_percent"
                ],
                ranked_entity_classes=frozenset(
                    params["similarity"]["ranked_entity_classes"]
                ),
            ),
            index=TokenOverlapIndex(
                corpus=corpus,
                index_version=params["similarity"]["index_version"],
            ),
        )
    )
    operators.register(
        TemporalAsOf(
            parameters=TemporalAsOfParameters(
                require_valid_at_boundary=params["temporal"][
                    "require_valid_at_boundary"
                ]
            )
        )
    )
    operators.register(
        TraversalNeighborhood(
            parameters=TraversalNeighborhoodParameters(
                seed_entity_classes=frozenset(
                    params["traversal"]["seed_entity_classes"]
                ),
                relationship_types=frozenset(
                    params["traversal"]["relationship_types"]
                ),
                depth_limit=params["traversal"]["depth_limit"],
            )
        )
    )
    return operators
