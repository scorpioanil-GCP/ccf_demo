"""End-to-end ``build_replay_record`` drives for the three HITL primitives
whose replay coverage was compositional (07-18; D-IMPL-66 item c).

The ApprovalGate slice (``tests/workflow/test_slice.py``) already drives the
full path — primitive action → resolution → ``build_replay_record`` →
assertion on the resulting :class:`~ccf.replay.record.DecisionReplayRecord`.
This module gives :class:`~ccf.hitl.escalation.ExceptionEscalation`,
:class:`~ccf.hitl.override.OverrideBoundary`, and
:class:`~ccf.hitl.review_queue.ReviewQueue` the same full-path proof,
closing the gate-row-7 narrowing named by the Codex/Cursor consensus:
each primitive's ``hitl_actions_block`` must land verbatim (byte-equal) on
replay dimension 2 (``replay.policy_bindings.hitl_actions``), and the block
must round-trip to its typed action record.

Every approver identity and event value lives in the banking fixtures
(No-Hardcoding Rule §6.4); this module carries mechanism-shaped drives only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.contracts.claims import LineageEntry
from ccf.controlplane.audit import AuditLog
from ccf.graph.protocols import GraphView
from ccf.hitl.escalation import (
    EscalationActionRecord,
    EscalationHandOff,
    EscalationResolution,
    ExceptionEscalation,
    ExplicitEscalation,
)
from ccf.hitl.override import (
    OverrideActionRecord,
    OverrideBoundary,
    OverrideResolution,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.review_queue import (
    ReviewActionRecord,
    ReviewQueue,
    ReviewQueueItem,
    ReviewResolution,
)
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    NO_HITL_ACTIONS,
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


class _Determination(CCFContract):
    """A deployment-shaped agent output; its values live in the fixture."""

    subject_uri: str
    determination: str


def _hitl() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "hitl.yaml").read_text()
    )
    return loaded


def _clock() -> Any:
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


def _principal(
    fixture: dict[str, Any],
    approver_key: str = "credit_officer",
    *,
    product_content_hash: str,
) -> HumanPrincipalBinding:
    approver = fixture["approvers"][approver_key]
    return HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _replay_record(*, hitl_actions: str | None) -> DecisionReplayRecord:
    """The 07-07 slice's builder shape, threading a primitive's verbatim
    block through the ``hitl_actions`` keyword into dimension 2."""
    boundary = datetime(2026, 2, 1, tzinfo=UTC)
    execution = ExecutionResult(
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
        view=GraphView(tenant_id="acme-bank", as_of=boundary),
    )
    product = ContextProductContract(
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id="acme-bank",
        temporal_boundary=boundary,
        expires_at=datetime(2026, 4, 1, tzinfo=UTC),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=boundary,
        ),
        payload={"k": "v"},
    )
    return build_replay_record(
        execution=execution,
        product=product,
        perspective=Perspective(principal_id="principal-1", role="analyst"),
        policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
        assembly_mode="algorithmic",
        recorded_at=datetime(2026, 3, 1, tzinfo=UTC),
        hitl_actions=hitl_actions,
    )


# --- E2E-1: ExceptionEscalation ----------------------------------------------


def _resolve_escalation(fixture: dict[str, Any]) -> EscalationResolution:
    transport = InMemoryHitlTransport()
    escalation = ExceptionEscalation(
        transport=transport, audit=AuditLog(), clock=_clock()
    )
    document = fixture["escalation"]["event"]
    trigger = ExplicitEscalation(
        reason=fixture["escalation"]["explicit_reason"]
    )
    hand_off = escalation.escalate(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        product_content_hash=content_hash(trigger),
        policy_ref=document["policy_ref"],
        trigger=trigger,
    )
    assert isinstance(hand_off, EscalationHandOff)
    resolution = escalation.resolve(
        tenant=document["tenant"],
        event_key=document["event_key"],
        action="approve",
        principal=_principal(
            fixture, product_content_hash=hand_off.event.product_content_hash
        ),
    )
    assert isinstance(resolution, EscalationResolution)
    return resolution


def test_an_escalation_resolution_lands_on_dimension_2_verbatim() -> None:
    """Full path: escalate → resolve → build_replay_record → the block is
    byte-equal on ``replay.policy_bindings.hitl_actions`` and round-trips
    to an EscalationActionRecord carrying the approver's subject_id."""
    fixture = _hitl()
    resolution = _resolve_escalation(fixture)
    replay = _replay_record(hitl_actions=resolution.hitl_actions_block)
    assert (
        replay.policy_bindings.hitl_actions == resolution.hitl_actions_block
    )
    record = EscalationActionRecord.model_validate_json(
        replay.policy_bindings.hitl_actions
    )
    subject_id = fixture["approvers"]["credit_officer"]["identity"][
        "subject_id"
    ]
    assert record.submission.principal.approver.subject_id == subject_id
    assert record.accepted is True


# --- E2E-2: OverrideBoundary --------------------------------------------------


def test_an_override_resolution_lands_on_dimension_2_verbatim() -> None:
    """Full path: propose → resolve(substitute) → build_replay_record →
    byte-equal landing, and BOTH the original and the override are present
    in the deserialized action record (CLAUDE.md §8.2 override doctrine)."""
    fixture = _hitl()
    transport = InMemoryHitlTransport()
    boundary: OverrideBoundary[_Determination] = OverrideBoundary(
        transport=transport, audit=AuditLog(), clock=_clock()
    )
    document = fixture["override"]["event"]
    original = _Determination(**fixture["override"]["original"])
    substitute = _Determination(**fixture["override"]["substitute"])
    pending = boundary.propose(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        original=original,
        policy_ref=document["policy_ref"],
    )
    resolution = boundary.resolve(
        tenant=document["tenant"],
        event_key=document["event_key"],
        principal=_principal(
            fixture, product_content_hash=pending.product_content_hash
        ),
        override=substitute,
    )
    assert isinstance(resolution, OverrideResolution)
    replay = _replay_record(hitl_actions=resolution.hitl_actions_block)
    assert (
        replay.policy_bindings.hitl_actions == resolution.hitl_actions_block
    )
    record = OverrideActionRecord[_Determination].model_validate_json(
        replay.policy_bindings.hitl_actions
    )
    assert record.original == original
    assert record.final == substitute
    assert record.overridden is True


# --- E2E-3a/3b: ReviewQueue ---------------------------------------------------


def _reviewed(
    fixture: dict[str, Any], *, released: bool
) -> ReviewResolution:
    transport = InMemoryHitlTransport()
    queue = ReviewQueue(
        transport=transport, audit=AuditLog(), clock=_clock()
    )
    document = fixture["review"]["event"]
    item = ReviewQueueItem(
        output_ref=fixture["review"]["item"]["output_ref"],
        lineage=tuple(
            LineageEntry(**entry)
            for entry in fixture["review"]["item"]["lineage"]
        ),
    )
    pending = queue.submit_for_review(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        item=item,
        policy_ref=document["policy_ref"],
    )
    principal = _principal(
        fixture, product_content_hash=pending.product_content_hash
    )
    action = queue.release if released else queue.reject
    resolution = action(
        tenant=document["tenant"],
        event_key=document["event_key"],
        principal=principal,
    )
    assert isinstance(resolution, ReviewResolution)
    return resolution


def test_a_review_release_lands_on_dimension_2_verbatim() -> None:
    """Full path (3a): submit_for_review → release → build_replay_record →
    byte-equal landing and typed round-trip with ``released=True``."""
    fixture = _hitl()
    resolution = _reviewed(fixture, released=True)
    replay = _replay_record(hitl_actions=resolution.hitl_actions_block)
    assert (
        replay.policy_bindings.hitl_actions == resolution.hitl_actions_block
    )
    record = ReviewActionRecord.model_validate_json(
        replay.policy_bindings.hitl_actions
    )
    assert record.released is True
    subject_id = fixture["approvers"]["credit_officer"]["identity"][
        "subject_id"
    ]
    assert record.submission.principal.approver.subject_id == subject_id


def test_a_review_rejection_lands_on_dimension_2_verbatim() -> None:
    """Full path (3b): submit_for_review → reject → build_replay_record →
    a rejection is a recorded action landing verbatim, never an absence."""
    fixture = _hitl()
    resolution = _reviewed(fixture, released=False)
    replay = _replay_record(hitl_actions=resolution.hitl_actions_block)
    assert (
        replay.policy_bindings.hitl_actions == resolution.hitl_actions_block
    )
    record = ReviewActionRecord.model_validate_json(
        replay.policy_bindings.hitl_actions
    )
    assert record.released is False


# --- negative guard -----------------------------------------------------------


def test_an_unthreaded_resolution_leaves_the_positive_sentinel() -> None:
    """A caller with a resolution in hand that does NOT thread the block
    leaves the positive NO_HITL_ACTIONS sentinel on dimension 2 — never the
    block. Landing the block is the caller's replay obligation (the honest
    boundary): the sentinel makes the skipped path detectable, it does not
    enforce the landing."""
    fixture = _hitl()
    resolution = _resolve_escalation(fixture)
    skipped = _replay_record(hitl_actions=None)
    assert skipped.policy_bindings.hitl_actions == NO_HITL_ACTIONS
    assert (
        skipped.policy_bindings.hitl_actions != resolution.hitl_actions_block
    )
