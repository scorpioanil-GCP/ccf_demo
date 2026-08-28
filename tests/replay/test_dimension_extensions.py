"""I.4 replay-dimension extensions (07-05): HITL actions on dimension 2,
workflow step sequences on dimension 5, workflow chains on dimension 4.

The claims, each pinned by a test that fails if the extension is done wrong:

1. **The record still has exactly five top-level dimensions** (INV-CH7-80).
   The HITL block extends ``PolicyBindingsSnapshot``; the workflow step
   sequence extends ``ContentGenerationPath``; workflow chains flow through
   the *existing* ``delegation_chain`` field. A sixth block would be a
   whitepaper-fidelity defect, not an option.
2. **"No HITL action / no workflow" is asserted, not absent** — positive
   sentinels in the ``MODE_1_MODEL_VERSION`` voice, never ``None``.
3. **Supplied blocks are recorded verbatim** — byte-equal to what the caller
   pre-serialized, never reconstructed here (T-07-09).
4. **A record built without HITL/workflow input is byte-identical to a
   pre-phase record except for the sentinel fields** — no contract break for
   existing callers.
5. **Two tenants' records carrying HITL/workflow blocks stay distinct and
   correctly attributed** (D-23; Ollama S5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.graph.protocols import GraphView
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.artifacts.file_store import FileArtifactStore
from ccf.replay.engine import resolve_artifact
from ccf.replay.record import (
    NO_ASSEMBLY_REFUSAL,
    FalseAssemblyRefusalClaimError,
    mint_assembly_refusal,
    NO_ADAPTER,
    NO_AGENT_DEFINITION,
    NO_GRAPH_QUERIES,
    NO_HITL_ACTIONS,
    NO_WORKFLOW_TRACE,
    ContentGenerationPath,
    DecisionReplayRecord,
    PerspectiveConditioning,
    PolicyBinding,
    PolicyBindingsSnapshot,
    build_replay_record,
)
from tests.replay.test_harness_trace import PRE_CHANGE_CANONICAL
from tests.replay.test_query_sequence_pin import _stored_verbatim

NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 2, 1, tzinfo=UTC)
EXPIRES = datetime(2026, 4, 1, tzinfo=UTC)


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


#: The five dimensions of whitepaper §7.10.1, by field name — the INV-CH7-80
#: structural assertion, written against the set rather than a field count so
#: it fails for the right reason if a sixth block ever appears.
FIVE_DIMENSIONS = frozenset(
    {
        "context_fabric_snapshot",
        "policy_bindings",
        "model_version",
        "perspective_conditioning",
        "content_generation_path",
    }
)

#: A pre-serialized HITL-actions block as a HITL primitive (07-07/07-08) would
#: pass it: canonical bytes the caller produced, decoded to the str the field
#: carries. The builder must record it verbatim.
HITL_BLOCK = canonical_bytes(
    [
        {
            "action": "approve",
            "approver_id": "approver-9",
            "gate_id": "gate-1",
            "acted_at": datetime(2026, 3, 1, 11, 59, tzinfo=UTC),
        }
    ]
).decode("utf-8")

#: A pre-serialized workflow step-sequence block as the engine (07-06) would
#: pass it.
WORKFLOW_BLOCK = canonical_bytes(
    {
        "execution_id": "wf-exec-1",
        "steps": [
            {"node": "assemble", "state": "completed"},
            {"node": "approve", "state": "completed"},
        ],
    }
).decode("utf-8")


def test_the_record_still_has_exactly_five_dimensions() -> None:
    """INV-CH7-80: both extensions land inside existing dimensions."""
    dimensions = set(DecisionReplayRecord.model_fields) - {"tenant_id", "recorded_at"}
    assert dimensions == FIVE_DIMENSIONS
    assert len(dimensions) == 5
    assert "hitl_actions" not in DecisionReplayRecord.model_fields
    assert "workflow_step_sequence" not in DecisionReplayRecord.model_fields
    assert "hitl_actions" in PolicyBindingsSnapshot.model_fields
    assert "workflow_step_sequence" in ContentGenerationPath.model_fields
    # 24.1.1-04 (D-60): the third extension lands the same way — inside an
    # existing dimension, never as a sixth top-level field.
    assert "assembly_refusal" not in DecisionReplayRecord.model_fields
    assert "assembly_refusal" in ContentGenerationPath.model_fields


def test_no_hitl_and_no_workflow_are_asserted_rather_than_absent() -> None:
    """Positive sentinels, never ``None`` — the ``MODE_1_MODEL_VERSION`` voice."""
    record = _build()
    assert record.policy_bindings.hitl_actions == NO_HITL_ACTIONS
    assert record.content_generation_path.workflow_step_sequence == NO_WORKFLOW_TRACE
    assert record.policy_bindings.hitl_actions is not None
    assert record.content_generation_path.workflow_step_sequence is not None
    # Present in the serialized form — the claims are positive.
    produced = canonical_bytes(record)
    assert NO_HITL_ACTIONS.encode() in produced
    assert NO_WORKFLOW_TRACE.encode() in produced


def test_a_supplied_hitl_block_lands_on_dimension_2_verbatim() -> None:
    """Recorded verbatim, byte-equal to what was passed (T-07-09)."""
    record = _build(hitl_actions=HITL_BLOCK)
    assert record.policy_bindings.hitl_actions == HITL_BLOCK
    assert record.policy_bindings.hitl_actions.encode("utf-8") == HITL_BLOCK.encode(
        "utf-8"
    )
    # Dimension 2's pre-existing content is untouched by the extension.
    assert record.policy_bindings.bindings == (
        PolicyBinding(key="policy.bundle", version="v1"),
    )


def test_a_supplied_workflow_block_lands_on_dimension_5_verbatim() -> None:
    record = _build(workflow_step_sequence=WORKFLOW_BLOCK)
    assert record.content_generation_path.workflow_step_sequence == WORKFLOW_BLOCK
    assert record.content_generation_path.workflow_step_sequence.encode(
        "utf-8"
    ) == WORKFLOW_BLOCK.encode("utf-8")
    # Dimension 5's pre-existing fields are untouched.
    assert record.content_generation_path.plan_id == "plan-1"
    assert record.content_generation_path.operator_plan == ("traversal.neighbors",)


def test_passing_none_is_indistinguishable_from_omitting_the_arguments() -> None:
    """The extension changes no existing caller's behavior."""
    assert canonical_bytes(_build()) == canonical_bytes(
        _build(hitl_actions=None, workflow_step_sequence=None)
    )


def test_records_round_trip_through_canonical_serialization() -> None:
    """Canonical bytes are stable and content-addressable for extended records."""
    record = _build(hitl_actions=HITL_BLOCK, workflow_step_sequence=WORKFLOW_BLOCK)
    again = _build(hitl_actions=HITL_BLOCK, workflow_step_sequence=WORKFLOW_BLOCK)
    assert canonical_bytes(record) == canonical_bytes(again)
    assert content_hash(record) == content_hash(again)
    rehydrated = DecisionReplayRecord.model_validate(record.model_dump())
    assert canonical_bytes(rehydrated) == canonical_bytes(record)


def test_two_tenants_records_stay_distinct_and_correctly_attributed() -> None:
    """D-23 / Ollama S5 — no shared structure leaks across principals."""
    first = _build(
        tenant_id="tenant-a",
        principal_id="principal-1",
        hitl_actions=HITL_BLOCK,
        workflow_step_sequence=WORKFLOW_BLOCK,
    )
    other_block = canonical_bytes(
        [{"action": "reject", "approver_id": "approver-2", "gate_id": "gate-9"}]
    ).decode("utf-8")
    second = _build(
        tenant_id="tenant-b",
        principal_id="principal-2",
        hitl_actions=other_block,
    )

    assert first.tenant_id == "tenant-a"
    assert second.tenant_id == "tenant-b"
    assert first.policy_bindings.hitl_actions == HITL_BLOCK
    assert second.policy_bindings.hitl_actions == other_block
    assert first.content_generation_path.workflow_step_sequence == WORKFLOW_BLOCK
    assert second.content_generation_path.workflow_step_sequence == NO_WORKFLOW_TRACE
    assert first.perspective_conditioning.principal_id == "principal-1"
    assert second.perspective_conditioning.principal_id == "principal-2"
    assert (
        first.context_fabric_snapshot.graph_snapshot_id
        != second.context_fabric_snapshot.graph_snapshot_id
    )


def test_the_extended_blocks_are_closed_world() -> None:
    """``extra=forbid`` still holds on both extended dimensions."""
    with pytest.raises(ValidationError):
        PolicyBindingsSnapshot(bindings=(), unexpected="x")  # type: ignore[call-arg]


# --- Task 2: dimension 4 delegation-chain extension (workflow chains) ------


def test_a_workflow_multi_element_delegation_chain_is_recorded_in_order() -> None:
    """The :258-266 commitment: workflow chains extend the EXISTING field.

    A workflow execution id plus two agent identities (D-23's two-agent case)
    flow through ``delegation_chain`` with no contract change, order preserved.
    """
    chain = ("wf-exec-1", "agent-alpha@1.0.0", "agent-beta@2.1.0")
    conditioning = PerspectiveConditioning(
        principal_id="principal-1",
        role="analyst",
        agent_definition_hash="hash-beta",
        agent_definition_uri="ccf://agents/beta@2.1.0",
        archetype_composition=("WorkflowAgent",),
        delegation_chain=chain,
    )
    record = _build(agent_conditioning=conditioning)
    assert record.perspective_conditioning.delegation_chain == chain
    # Canonical serialization preserves the order (order is meaningful).
    produced = canonical_bytes(record)
    assert (
        b'"delegation_chain":["wf-exec-1","agent-alpha@1.0.0","agent-beta@2.1.0"]'
        in produced
    )


def test_two_tenants_workflow_chains_do_not_cross_contaminate() -> None:
    """Ollama S5 two-tenant variant for dimension 4 workflow chains."""
    chain_a = ("wf-exec-a", "agent-one@1.0.0", "agent-two@1.0.0")
    chain_b = ("wf-exec-b", "agent-three@1.0.0")
    first = _build(
        tenant_id="tenant-a",
        agent_conditioning=PerspectiveConditioning(
            principal_id="principal-1", role="analyst", delegation_chain=chain_a
        ),
    )
    second = _build(
        tenant_id="tenant-b",
        agent_conditioning=PerspectiveConditioning(
            principal_id="principal-2", role="analyst", delegation_chain=chain_b
        ),
    )
    assert first.perspective_conditioning.delegation_chain == chain_a
    assert second.perspective_conditioning.delegation_chain == chain_b
    assert first.tenant_id == "tenant-a"
    assert second.tenant_id == "tenant-b"


def test_a_pre_workflow_record_still_carries_the_single_element_sentinel() -> None:
    """Pre-agent records are unchanged: the single-element chain survives."""
    record = _build()
    assert record.perspective_conditioning.delegation_chain == ("principal-1",)
    assert record.perspective_conditioning.agent_definition_hash == NO_AGENT_DEFINITION


# --- 15.4-08: dimension 2 gains the adapter pin ------------------------------


def test_a_record_written_before_the_adapter_pin_still_resolves(
    tmp_path: Any,
) -> None:
    """V16 — the D-IMPL-89 regression, extended to the 15.4-08 pin.

    ``PRE_CHANGE_CANONICAL`` was captured from a builder that predates every
    record extension, including this one. It is **reused, never re-authored**:
    the claim is that a record nobody has touched still works, and a fixture
    written today cannot demonstrate that — it would only show the builder
    agreeing with itself.

    Resolution is the assertion. :func:`~ccf.replay.engine.resolve_artifact`
    raises :class:`~ccf.replay.engine.ReplayDivergence` when the stored bytes
    do not hash to the address asked for, so a return value *is* "no
    divergence". It holds because D-IMPL-89 verifies the sha256 of the raw
    fetched bytes **before** model validation; re-hashing a revalidated model
    would serialize the three fields this plan added and reject an honest
    pre-extension record as tampered.
    """
    store = FileArtifactStore(root=tmp_path / "artifacts")
    address = _stored_verbatim(store, PRE_CHANGE_CANONICAL)

    record = resolve_artifact(
        store=store, content_address=address, contract=DecisionReplayRecord
    )

    # The rebuilt record asserts the three positive claims rather than going
    # quiet: "this decision did not record which adapter answered".
    assert record.policy_bindings.graph_adapter == NO_ADAPTER
    assert record.policy_bindings.graph_adapter_version == NO_ADAPTER
    assert record.policy_bindings.graph_secret_refs == ()

    # The earlier extensions' sentinels are still intact on the same bytes —
    # each extension must keep the previous ones' compatibility, not just its
    # own.
    assert record.policy_bindings.hitl_actions == NO_HITL_ACTIONS
    assert record.policy_bindings.survivor_cap is None
    assert record.content_generation_path.workflow_step_sequence == NO_WORKFLOW_TRACE
    assert record.content_generation_path.graph_query_sequence == NO_GRAPH_QUERIES
    assert record.context_fabric_snapshot.source_attestation is None


# --- D-60 / D-IMPL-214 Reading B: a refusal has an identity ------------------


def _violation() -> Any:
    from ccf.products.request import ProductRequestViolation

    return ProductRequestViolation(
        reason="class-mismatch",
        key="schema_name",
        detail="the question addresses a class this agent does not answer",
        declared_type="declared.class",
        presented_type="presented.class",
        declared_keys=frozenset({"schema_name"}),
        presented_keys=frozenset({"schema_name"}),
    )


def test_a_decision_that_met_no_refusal_asserts_so_rather_than_being_silent() -> None:
    """The positive sentinel, in the ``NO_HITL_ACTIONS`` voice."""
    record = _build()
    assert record.content_generation_path.assembly_refusal == NO_ASSEMBLY_REFUSAL
    assert b'"assembly_refusal":"no-assembly-refusal"' in canonical_bytes(record)


def test_the_block_is_minted_from_the_assemblers_return_value() -> None:
    """Leg 1: derived, never hand-claimed."""
    violation = _violation()
    block = mint_assembly_refusal(violation)
    assert block == canonical_bytes(violation).decode("utf-8")
    assert block != NO_ASSEMBLY_REFUSAL


def test_a_supplied_refusal_block_lands_on_dimension_5_verbatim() -> None:
    """Recorded as the caller minted it, not re-serialized by the builder."""
    block = mint_assembly_refusal(_violation())
    record = _build(assembly_refusal=block)
    assert record.content_generation_path.assembly_refusal == block


def test_a_false_no_refusal_claim_is_refused_at_write_time() -> None:
    """Leg 2, on ``FalseGrantClaimError``'s exact reasoning.

    A caller holding a refusal while asserting the no-refusal claim is
    recording something it already knows cannot be true.
    """
    with pytest.raises(FalseAssemblyRefusalClaimError) as caught:
        mint_assembly_refusal(_violation(), claimed=NO_ASSEMBLY_REFUSAL)
    assert "no-assembly-refusal" in str(caught.value)


def test_claiming_a_refusal_that_did_not_happen_is_refused_too() -> None:
    """The symmetric case: asserting a refusal over an outcome that is not one."""
    outcome = object()
    with pytest.raises(FalseAssemblyRefusalClaimError):
        mint_assembly_refusal(outcome, claimed="something-that-is-not-the-sentinel")  # type: ignore[arg-type]


def test_a_fabricated_refusal_block_is_refused_by_the_builder() -> None:
    """Leg 3: a block that merely LOOKS like a refusal cannot be recorded."""
    with pytest.raises(ValueError) as caught:
        _build(assembly_refusal='{"looks":"like a refusal"}')
    assert "governed refusal" in str(caught.value)


def test_passing_none_is_indistinguishable_from_omitting_the_refusal() -> None:
    """The sentinel-default discipline: no existing call site moves."""
    assert canonical_bytes(_build()) == canonical_bytes(_build(assembly_refusal=None))
