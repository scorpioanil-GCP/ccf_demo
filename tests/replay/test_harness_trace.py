"""D-25 — the harness-attributable extension of replay dimension 3.

Four claims, each pinned by a test that fails if the extension is done wrong:

1. **The record still has exactly five top-level dimensions** (INV-CH7-80).
   `harness_trace` extends `ModelVersionRecord`; a sixth block would be a
   whitepaper-fidelity defect, not an option.
2. **The extension changes nothing that existed before it.** Every field the
   builder wrote before D-25 is byte-for-byte what it was, asserted against a
   literal captured from the pre-change implementation, and passing
   `harness_trace=None` is indistinguishable from omitting the argument.
3. **"No harness participated" is asserted, not absent** — the positive
   `NO_HARNESS` sentinel, in the `MODE_1_MODEL_VERSION` voice.
4. **Two agents carry their own traces and their own governed fields** (D-23):
   nothing here is computed over a structure shared between principals.

The D-18 portability split is the reason the block is named: the fields here
are exactly what the three-adapter equivalence comparison excludes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.protocols import GraphView
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    MODE_1_MODEL_VERSION,
    NO_HARNESS,
    NO_HARNESS_TRACE,
    DecisionReplayRecord,
    HarnessTrace,
    ModelVersionRecord,
    PolicyBinding,
    build_replay_record,
)

NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 2, 1, tzinfo=UTC)
EXPIRES = datetime(2026, 4, 1, tzinfo=UTC)

#: Canonical bytes of the record the **pre-change** ``build_replay_record``
#: produced over :func:`_execution` / :func:`_product` / :func:`_build`'s
#: arguments, captured by executing `git show HEAD:src/ccf/replay/record.py`
#: before the D-25 edit landed. Byte-identity is scoped honestly (D-21): this
#: literal is what the builder emitted, and the post-change builder emits
#: exactly these bytes plus dimension 3's one new ``harness_trace`` key.
PRE_CHANGE_CANONICAL = (
    b'{"content_generation_path":{"operator_plan":["traversal.neighbors"],'
    b'"plan_id":"plan-1","product_content_address":'
    b'"e1fa788d7346269d7cc89b47b01021d547382f3eb5b0bc2f3b00a5cf9ef8c05f",'
    b'"steps":[{"category":"traversal","operator_key":"traversal.neighbors",'
    b'"parameter_hash":"ph-1"}]},"context_fabric_snapshot":'
    b'{"graph_snapshot_id":'
    b'"490b727114dc9d131ef9fed53494003d1c3466b62049fb0b9bdbe5ee7d8ed567",'
    b'"store_watermark":'
    b'"eab08ae353fdceadab93a2b4c94ca69ddf1be1a19ff1c3806567b32cb0f1f593",'
    b'"temporal_boundary":"2026-02-01T00:00:00.000000Z","tenant_id":"tenant-a",'
    b'"touched_entities":[],"touched_relationships":[]},"model_version":'
    b'{"assembly_mode":"algorithmic","model_version":"none"},'
    b'"perspective_conditioning":{"agent_definition_hash":"no-agent",'
    b'"agent_definition_uri":"no-agent","archetype_composition":[],'
    b'"delegation_chain":["principal-1"],"grant_set_hash":"no-grants",'
    b'"principal_id":"principal-1","role":"analyst"},"policy_bindings":'
    b'{"bindings":[{"key":"policy.bundle","version":"v1"}]},'
    b'"recorded_at":"2026-03-01T12:00:00.000000Z","tenant_id":"tenant-a"}'
)


def _execution(*, plan_id: str = "plan-1", tenant_id: str = "tenant-a") -> ExecutionResult:
    return ExecutionResult(
        plan_id=plan_id,
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash="ph-1",
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(plan_id=plan_id, payload={"k": "v"}),
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
    tenant_id = overrides.pop("tenant_id", "tenant-a")
    principal_id = overrides.pop("principal_id", "principal-1")
    return build_replay_record(
        execution=_execution(tenant_id=tenant_id),
        product=_product(tenant_id=tenant_id),
        perspective=Perspective(principal_id=principal_id, role="analyst"),
        policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
        assembly_mode="algorithmic",
        recorded_at=NOW,
        **overrides,
    )


#: The five dimensions of whitepaper §7.10.1, by field name. ``tenant_id`` and
#: ``recorded_at`` are record-level metadata, not dimensions — which is why the
#: INV-CH7-80 assertion is written against this set rather than against
#: ``len(model_fields)``, a count that was 7 before this extension and would
#: pass or fail for the wrong reason.
FIVE_DIMENSIONS = frozenset(
    {
        "context_fabric_snapshot",
        "policy_bindings",
        "model_version",
        "perspective_conditioning",
        "content_generation_path",
    }
)


def test_the_record_still_has_exactly_five_dimensions() -> None:
    """INV-CH7-80: the extension lands inside dimension 3, never beside it."""
    dimensions = set(DecisionReplayRecord.model_fields) - {"tenant_id", "recorded_at"}
    assert dimensions == FIVE_DIMENSIONS
    assert len(dimensions) == 5
    assert "harness_trace" not in DecisionReplayRecord.model_fields
    assert "harness_trace" in ModelVersionRecord.model_fields


def test_no_harness_is_asserted_rather_than_absent() -> None:
    """A decision no harness mediated says so (the ``MODE_1_MODEL_VERSION`` voice).

    The failure this pins: an absent trace and a *dropped* trace would be the
    same artifact, so a lost attribution would read as an honest no-harness run.
    """
    record = _build()
    trace = record.model_version.harness_trace
    assert trace == NO_HARNESS_TRACE
    assert trace.harness_id == NO_HARNESS
    assert trace.trace_provider == NO_HARNESS
    assert trace.trace_id == NO_HARNESS
    # The field is present in the serialized form — the claim is positive.
    assert b'"harness_id":"no-harness"' in canonical_bytes(record)


def test_passing_none_is_indistinguishable_from_omitting_the_argument() -> None:
    """The extension changes no existing behavior."""
    assert canonical_bytes(_build()) == canonical_bytes(_build(harness_trace=None))


def test_every_pre_change_field_is_byte_for_byte_unchanged() -> None:
    """Byte-identity, scoped to what the claim can actually earn (D-21).

    Dimension 3 gains exactly one key; everything else the builder emits is
    identical to the pre-change implementation's output, compared against a
    literal captured from it.
    """
    record = _build(harness_trace=None)
    produced = canonical_bytes(record)

    # The only differences from the pre-change bytes are the named extension
    # keys: dimension 3's harness block (I.3, D-25), the I.4 sentinel fields
    # on dimensions 2 and 5 (07-05: hitl_actions, workflow_step_sequence),
    # the 15.2-08 sentinel fields on the same two dimensions (D-10/D-11:
    # survivor_cap, graph_query_sequence), and the 15.2-11 sentinel field on
    # dimension 1 (D-09: source_attestation). Removing exactly those
    # reproduces the captured literal — "byte-identical except for the
    # sentinel fields".
    assert produced.replace(
        b'"harness_trace":{"harness_id":"no-harness","input_tokens":0,'
        b'"model_version":"no-harness","output_tokens":0,'
        b'"trace_id":"no-harness","trace_provider":"no-harness"},',
        b"",
    ).replace(
        b',"hitl_actions":"no-hitl-actions"',
        b"",
    ).replace(
        b',"workflow_step_sequence":"no-workflow-trace"',
        b"",
    ).replace(
        b'"graph_query_sequence":[],',
        b"",
    ).replace(
        b',"survivor_cap":null',
        b"",
    ).replace(
        b'"source_attestation":null,',
        b"",
    ) == PRE_CHANGE_CANONICAL

    # Dimension 3's two pre-existing fields are untouched by the extension.
    assert record.model_version.assembly_mode == "algorithmic"
    assert record.model_version.model_version == MODE_1_MODEL_VERSION


def test_a_supplied_trace_is_recorded_verbatim() -> None:
    """Derived from what the adapter reported, never reconstructed here."""
    reported = HarnessTrace(
        harness_id="claude-agent-sdk",
        model_version="claude-opus-5-20260501",
        trace_provider="langsmith",
        trace_id="trace-abc",
        input_tokens=1234,
        output_tokens=56,
    )
    record = _build(harness_trace=reported)
    assert record.model_version.harness_trace == reported
    assert canonical_bytes(record.model_version.harness_trace) == canonical_bytes(
        reported
    )


def test_a_harness_trace_cannot_overwrite_a_governed_field() -> None:
    """T-06-62: the harness writes its own block and nothing else.

    The harness reports its own ``model_version``; the fabric's dimension-3
    ``model_version`` stays the fabric's claim about what *it* invoked.
    """
    record = _build(
        harness_trace=HarnessTrace(
            harness_id="langgraph", model_version="some-model-the-harness-ran"
        )
    )
    assert record.model_version.model_version == MODE_1_MODEL_VERSION
    assert record.model_version.harness_trace.model_version == (
        "some-model-the-harness-ran"
    )


def test_two_agents_carry_their_own_traces_and_governed_fields() -> None:
    """D-23 — the multi-principal case, not just the happy single-principal path.

    Nothing in the extension is computed over a structure shared between
    principals, so two records built in the same process under different
    tenants and principals agree on nothing they should not.
    """
    first = _build(
        tenant_id="tenant-a",
        principal_id="principal-1",
        harness_trace=HarnessTrace(harness_id="google-adk", trace_id="trace-a"),
    )
    second = _build(
        tenant_id="tenant-b",
        principal_id="principal-2",
        harness_trace=HarnessTrace(harness_id="langgraph", trace_id="trace-b"),
    )

    assert first.model_version.harness_trace.harness_id == "google-adk"
    assert second.model_version.harness_trace.harness_id == "langgraph"
    assert first.model_version.harness_trace != second.model_version.harness_trace

    # Governed fields are per-principal too — no shared structure leaked across.
    assert first.tenant_id == "tenant-a"
    assert second.tenant_id == "tenant-b"
    assert first.perspective_conditioning.principal_id == "principal-1"
    assert second.perspective_conditioning.principal_id == "principal-2"
    assert (
        first.context_fabric_snapshot.graph_snapshot_id
        != second.context_fabric_snapshot.graph_snapshot_id
    )

    # And a third record built with no harness still asserts the positive
    # no-harness claim while the other two hold their own.
    third = _build(tenant_id="tenant-c", principal_id="principal-3")
    assert third.model_version.harness_trace == NO_HARNESS_TRACE
    assert first.model_version.harness_trace.harness_id == "google-adk"
    assert second.model_version.harness_trace.harness_id == "langgraph"


def test_the_trace_is_a_closed_world_contract() -> None:
    """``extra=forbid``: an unknown harness-reported key is refused, not carried."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        HarnessTrace(harness_id="langgraph", cost_usd="0.01")  # type: ignore[call-arg]
