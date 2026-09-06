"""D-IMPL-45 delivery (07-05): ExternalTraceProviderProtocol + TraceCorrelationHook.

The I.3 handoff (PHASE_I3_GATE §5): "TraceCorrelationHook attaches to the
harness_trace slot in I.4." Three claims, each pinned:

1. **The no-op is honest** — enrich-nothing means change-nothing: with the
   no-op reference provider, a trace passes through byte-identical.
2. **A supplied correlation lands INSIDE the existing dimension-3
   ``harness_trace`` slot** — the record still has exactly five dimensions,
   no new top-level slot, no new record field, no new sentinel (T-07-10).
3. **Correlation is captured at build time only** — the hook never runs at
   replay-read time; reading and serializing the record invokes no provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.protocols import GraphView
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.correlation import (
    ExternalTraceProviderProtocol,
    NoOpTraceProvider,
    TraceCorrelation,
    TraceCorrelationHook,
)
from ccf.replay.record import (
    NO_HARNESS,
    DecisionReplayRecord,
    HarnessTrace,
    ModelVersionRecord,
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)

NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 2, 1, tzinfo=UTC)
EXPIRES = datetime(2026, 4, 1, tzinfo=UTC)

FIVE_DIMENSIONS = frozenset(
    {
        "context_fabric_snapshot",
        "policy_bindings",
        "model_version",
        "perspective_conditioning",
        "content_generation_path",
    }
)


def _execution(*, tenant_id: str = "tenant-a") -> ExecutionResult:
    return ExecutionResult(
        plan_id="plan-1",
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash="ph-1",
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(plan_id="plan-1", payload={"k": "v"}),
        view=GraphView(tenant_id=tenant_id, as_of=BOUNDARY),
    )


def _product(*, tenant_id: str = "tenant-a") -> ContextProductContract:
    return ContextProductContract(
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id=tenant_id,
        temporal_boundary=BOUNDARY,
        expires_at=EXPIRES,
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload={"k": "v"},
    )


def _build(**overrides: Any) -> DecisionReplayRecord:
    return build_replay_record(
        execution=_execution(),
        product=_product(),
        perspective=Perspective(principal_id="principal-1", role="analyst"),
        policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
        assembly_mode="algorithmic",
        recorded_at=NOW,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        **overrides,
    )


class _CountingProvider:
    """A provider that reports a fixed correlation and counts its calls."""

    def __init__(self) -> None:
        self.calls = 0

    def correlate(self, *, execution_ref: str) -> TraceCorrelation | None:
        self.calls += 1
        return TraceCorrelation(
            trace_provider="langsmith", trace_id=f"trace-for-{execution_ref}"
        )


def test_the_no_op_provider_conforms_and_the_hook_changes_nothing() -> None:
    """The no-op is honest: enrich-nothing means change-nothing."""
    assert isinstance(NoOpTraceProvider(), ExternalTraceProviderProtocol)
    hook = TraceCorrelationHook(provider=NoOpTraceProvider())
    reported = HarnessTrace(
        harness_id="claude-agent-sdk",
        model_version="claude-opus-5-20260501",
        input_tokens=10,
        output_tokens=2,
    )
    enriched = hook.enrich(reported, execution_ref="exec-1")
    assert canonical_bytes(enriched) == canonical_bytes(reported)
    assert enriched == reported


def test_a_correlation_lands_inside_the_existing_harness_trace_slot() -> None:
    """T-07-10: the hook enriches the dim-3 slot and mints nothing new."""
    provider = _CountingProvider()
    hook = TraceCorrelationHook(provider=provider)
    assert isinstance(provider, ExternalTraceProviderProtocol)

    reported = HarnessTrace(harness_id="langgraph", model_version="some-model")
    enriched = hook.enrich(reported, execution_ref="exec-42")
    record = _build(harness_trace=enriched)

    # The payload is inside the existing dimension-3 harness_trace content.
    trace = record.model_version.harness_trace
    assert trace.trace_provider == "langsmith"
    assert trace.trace_id == "trace-for-exec-42"
    # Everything else the harness reported is untouched.
    assert trace.harness_id == "langgraph"
    assert trace.model_version == "some-model"

    # Structural assertion: still five dimensions, no new slot, no new field.
    dimensions = set(DecisionReplayRecord.model_fields) - {"tenant_id", "recorded_at"}
    assert dimensions == FIVE_DIMENSIONS
    assert set(HarnessTrace.model_fields) == {
        "harness_id",
        "model_version",
        "trace_provider",
        "trace_id",
        "input_tokens",
        "output_tokens",
    }
    assert "trace_correlation" not in ModelVersionRecord.model_fields


def test_no_correlation_leaves_the_positive_no_harness_claim() -> None:
    """A provider returning ``None`` leaves the trace's own values in force."""
    hook = TraceCorrelationHook(provider=NoOpTraceProvider())
    enriched = hook.enrich(HarnessTrace(), execution_ref="exec-1")
    assert enriched.trace_provider == NO_HARNESS
    assert enriched.trace_id == NO_HARNESS


def test_correlation_is_captured_at_build_time_only() -> None:
    """The hook never runs at replay-read time — verbatim doctrine preserved."""
    provider = _CountingProvider()
    hook = TraceCorrelationHook(provider=provider)
    enriched = hook.enrich(HarnessTrace(harness_id="adk"), execution_ref="exec-7")
    assert provider.calls == 1

    record = _build(harness_trace=enriched)
    # Reading and serializing the record — the replay-read path — invokes
    # nothing: the correlation is a stored value, not a live lookup.
    _ = record.model_version.harness_trace.trace_id
    _ = canonical_bytes(record)
    _ = DecisionReplayRecord.model_validate(record.model_dump())
    assert provider.calls == 1
