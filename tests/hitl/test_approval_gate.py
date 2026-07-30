"""``ApprovalGate`` + ``ApprovalSinkAdapter`` — the dual face (07-07).

Written before the implementation per the TDD discipline. The claims:

**The gate face** (async workflow face): a decision submitted without a
:class:`~ccf.hitl.principal.HumanPrincipalBinding` is unrepresentable
through the typed transport contract; approval and rejection both produce
audited outcomes; rejection is a *returned* typed value with a
``resolved=False`` audit record, never an exception; a TOCTOU hash
mismatch (the approver's binding names a product hash other than the one
bound at suspend time) is a returned typed refusal, audited
``resolved=False``.

**The sync grant face** (:class:`ApprovalSinkAdapter`): ``decide`` with no
completed decision bound raises a typed error — it never blocks on a
pending human and never fabricates a verdict. The adapter's conformance to
the ``ApprovalSink`` Protocol is asserted by the shared conformance suite
(``tests/conformance/test_approval_sink.py``), which this file does not
duplicate.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.controlplane.audit import AuditLog
from ccf.hitl.approval_gate import (
    ApprovalGate,
    ApprovalSinkAdapter,
    GateResolution,
    GateResolutionRefused,
    UnboundDecisionError,
    UnknownGateEventError,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import (
    HitlActionSubmission,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from ccf.skills.grants import ApprovalOutcome

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


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
    fixture: dict[str, Any], *, product_content_hash: str
) -> HumanPrincipalBinding:
    approver = fixture["approvers"]["credit_officer"]
    return HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _gate() -> tuple[ApprovalGate, InMemoryHitlTransport, AuditLog]:
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    gate = ApprovalGate(transport=transport, audit=audit, clock=_clock())
    return gate, transport, audit


def _event(fixture: dict[str, Any]) -> PendingHitlEvent:
    document = dict(fixture["event"])
    return PendingHitlEvent(
        **document, product_content_hash=content_hash(document)
    )


# --- the gate face ------------------------------------------------------------


def test_a_submission_without_a_binding_is_unrepresentable() -> None:
    """The typed transport contract requires the principal by type (07-04)."""
    fixture = _hitl()
    event = _event(fixture)
    with pytest.raises(ValidationError):
        HitlActionSubmission(  # type: ignore[call-arg]
            event_key=event.event_key,
            tenant=event.tenant,
            action="approve",
        )


def test_an_approval_is_an_audited_typed_resolution() -> None:
    fixture = _hitl()
    gate, transport, audit = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    resolution = gate.resolve(
        tenant=event.tenant,
        event_key=event.event_key,
        action="approve",
        principal=_principal(
            fixture, product_content_hash=event.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)
    assert isinstance(resolution.outcome, ApprovalOutcome)
    assert resolution.outcome.approved is True
    # The action is on the authority path and the event is consumed.
    assert len(transport.submissions(tenant=event.tenant)) == 1
    assert transport.pending(tenant=event.tenant) == ()
    events = [e for e in audit.events() if e.action == "hitl_action"]
    assert len(events) == 1 and events[0].resolved is True


def test_a_rejection_is_a_returned_value_with_a_resolved_false_audit() -> None:
    """Rejection is a governance verdict, never control flow."""
    fixture = _hitl()
    gate, transport, audit = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    resolution = gate.resolve(
        tenant=event.tenant,
        event_key=event.event_key,
        action="reject",
        principal=_principal(
            fixture, product_content_hash=event.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)
    assert resolution.outcome.approved is False
    events = [e for e in audit.events() if e.action == "hitl_action"]
    assert len(events) == 1 and events[0].resolved is False


def test_a_toctou_hash_mismatch_is_a_returned_audited_refusal() -> None:
    """The binding's hash must equal the hash bound at suspend time."""
    fixture = _hitl()
    gate, transport, audit = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    mutated_hash = content_hash({"mutated": "product"})
    assert mutated_hash != event.product_content_hash
    refusal = gate.resolve(
        tenant=event.tenant,
        event_key=event.event_key,
        action="approve",
        principal=_principal(fixture, product_content_hash=mutated_hash),
    )
    assert isinstance(refusal, GateResolutionRefused)
    # The refused event is NOT consumed and no action reached the authority
    # path: the human must re-review the current product version.
    assert transport.pending(tenant=event.tenant) == (event,)
    assert transport.submissions(tenant=event.tenant) == ()
    events = [e for e in audit.events() if e.action == "hitl_action"]
    assert len(events) == 1 and events[0].resolved is False


def test_resolving_an_unknown_event_raises() -> None:
    """Broken wiring raises; it is never a returned refusal (I.1 line)."""
    fixture = _hitl()
    gate, _, _ = _gate()
    event = _event(fixture)
    with pytest.raises(UnknownGateEventError):
        gate.resolve(
            tenant=event.tenant,
            event_key="no-such-event",
            action="approve",
            principal=_principal(
                fixture, product_content_hash=event.product_content_hash
            ),
        )


def test_the_resolution_carries_the_preserialized_dim_2_block() -> None:
    """The gate serializes the HITL-action block once; replay records it
    verbatim (07-05 keyword discipline)."""
    fixture = _hitl()
    gate, transport, _ = _gate()
    event = _event(fixture)
    transport.enqueue(event=event)
    resolution = gate.resolve(
        tenant=event.tenant,
        event_key=event.event_key,
        action="approve",
        principal=_principal(
            fixture, product_content_hash=event.product_content_hash
        ),
    )
    assert isinstance(resolution, GateResolution)
    block = resolution.hitl_actions_block
    assert (
        fixture["approvers"]["credit_officer"]["identity"]["subject_id"]
        in block
    )
    assert event.product_content_hash in block


# --- the sync grant face ------------------------------------------------------


def test_decide_with_no_bound_decision_raises_a_typed_error() -> None:
    """The sync face is honest: it never blocks, never fabricates."""
    adapter = ApprovalSinkAdapter()
    with pytest.raises(UnboundDecisionError):
        adapter.decide(object())  # type: ignore[arg-type]
