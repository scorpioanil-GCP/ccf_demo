"""HITLTransportProtocol + in-memory reference impl (D-IMPL-20).

Written before the implementation per the TDD discipline. The claims pinned
here: the transport is a *typed* queue — extra=forbid contracts in, the
same contracts out, never dicts; the authority path requires a
:class:`~ccf.hitl.principal.HumanPrincipalBinding` **by type**, so an
unattributed action submission is unrepresentable through the contract; and
queue views are per-tenant — two tenants' queues never interleave (D-23).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.hitl.transport import (
    HITL_ACTIONS,
    HITL_EVENT_CLASSES,
    HitlActionSubmission,
    HITLTransportProtocol,
    InMemoryHitlTransport,
    PendingHitlEvent,
)

ACTION_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)


def _binding() -> HumanPrincipalBinding:
    return HumanPrincipalBinding.model_validate(
        {
            "approver": {
                "subject_id": "credit-officer-7",
                "identity_provider_ref": "oidc:acme-bank-sso",
            },
            "authentication": {
                "method": "oidc",
                "assurance_level": "aal2",
                "session_ref": "session-01HZX",
            },
            "action_time": ACTION_TIME,
            "product_content_hash": content_hash({"product": "seen"}),
        }
    )


def _event(**mutations: Any) -> PendingHitlEvent:
    document: dict[str, Any] = {
        "event_key": "acme-bank/approvals/1",
        "event_class": "approval-gate",
        "tenant": "acme-bank",
        "workflow_state_ref": "workflow-state/covenant-review/run-1",
        "product_content_hash": content_hash({"product": "seen"}),
        "policy_ref": (
            "ccf-artifact://acme-bank/approval-policy/credit-officer@1.0.0"
        ),
    }
    document.update(mutations)
    return PendingHitlEvent.model_validate(document)


def _submission(**mutations: Any) -> HitlActionSubmission:
    document: dict[str, Any] = {
        "event_key": "acme-bank/approvals/1",
        "tenant": "acme-bank",
        "action": "approve",
        "principal": _binding(),
        "annotation": None,
    }
    document.update(mutations)
    return HitlActionSubmission.model_validate(document)


# --- the typed vocabulary -----------------------------------------------------


def test_the_four_hitl_primitives_have_event_classes() -> None:
    assert HITL_EVENT_CLASSES == frozenset(
        {
            "approval-gate",
            "exception-escalation",
            "override-boundary",
            "review-queue",
        }
    )
    assert HITL_ACTIONS == frozenset(
        {"approve", "reject", "override", "annotate"}
    )


def test_an_unknown_event_class_is_refused() -> None:
    with pytest.raises(ValidationError, match="event class"):
        _event(event_class="coffee-break")


def test_an_unknown_action_is_refused() -> None:
    with pytest.raises(ValidationError, match="action"):
        _submission(action="rubber-stamp")


def test_an_unpinned_policy_ref_is_refused() -> None:
    with pytest.raises(ValidationError, match="latest"):
        _event(
            policy_ref=(
                "ccf-artifact://acme-bank/approval-policy/"
                "credit-officer@latest"
            )
        )


# --- authority requires a principal binding by type (D-IMPL-21) ---------------


def test_a_submission_without_a_principal_binding_is_unrepresentable() -> None:
    document = {
        "event_key": "acme-bank/approvals/1",
        "tenant": "acme-bank",
        "action": "approve",
        "annotation": None,
    }
    with pytest.raises(ValidationError, match="principal"):
        HitlActionSubmission.model_validate(document)


def test_a_dict_in_place_of_the_binding_must_satisfy_the_contract() -> None:
    with pytest.raises(ValidationError):
        _submission(principal={"approver": "just-a-name"})


# --- the typed queue ----------------------------------------------------------


def test_enqueue_dequeue_preserves_typing() -> None:
    transport = InMemoryHitlTransport()
    event = _event()
    transport.enqueue(event=event)
    dequeued = transport.dequeue(tenant="acme-bank")
    assert isinstance(dequeued, PendingHitlEvent)
    assert dequeued == event
    assert transport.dequeue(tenant="acme-bank") is None


def test_pending_is_a_view_and_dequeue_is_fifo() -> None:
    transport = InMemoryHitlTransport()
    first = _event(event_key="acme-bank/approvals/1")
    second = _event(event_key="acme-bank/approvals/2")
    transport.enqueue(event=first)
    transport.enqueue(event=second)
    assert transport.pending(tenant="acme-bank") == (first, second)
    assert transport.dequeue(tenant="acme-bank") == first
    assert transport.pending(tenant="acme-bank") == (second,)


def test_submitted_actions_return_through_the_same_surface() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    submission = _submission()
    transport.submit(submission=submission)
    recorded = transport.submissions(tenant="acme-bank")
    assert recorded == (submission,)
    assert isinstance(recorded[0].principal, HumanPrincipalBinding)


def test_remove_takes_the_named_event_and_preserves_the_rest() -> None:
    """WR-02: removal is one atomic transport operation — the named event
    comes out, every other event keeps its relative order."""
    transport = InMemoryHitlTransport()
    first = _event(event_key="acme-bank/approvals/1")
    second = _event(event_key="acme-bank/approvals/2")
    third = _event(event_key="acme-bank/approvals/3")
    for event in (first, second, third):
        transport.enqueue(event=event)

    removed = transport.remove(tenant="acme-bank", event_key=second.event_key)

    assert removed == second
    assert transport.pending(tenant="acme-bank") == (first, third)


def test_remove_of_an_absent_event_returns_none() -> None:
    transport = InMemoryHitlTransport()
    assert transport.remove(tenant="acme-bank", event_key="missing") is None
    transport.enqueue(event=_event(event_key="acme-bank/approvals/1"))
    assert transport.remove(tenant="acme-bank", event_key="missing") is None
    # And exactly one of two sequential removes for the same key wins.
    key = "acme-bank/approvals/1"
    assert transport.remove(tenant="acme-bank", event_key=key) is not None
    assert transport.remove(tenant="acme-bank", event_key=key) is None


def test_queue_views_are_per_tenant() -> None:
    """D-23: two tenants' queues do not interleave."""
    transport = InMemoryHitlTransport()
    acme = _event(tenant="acme-bank", event_key="acme-bank/approvals/1")
    globex = _event(tenant="globex", event_key="globex/approvals/1")
    transport.enqueue(event=acme)
    transport.enqueue(event=globex)
    assert transport.pending(tenant="acme-bank") == (acme,)
    assert transport.pending(tenant="globex") == (globex,)
    assert transport.dequeue(tenant="globex") == globex
    assert transport.pending(tenant="acme-bank") == (acme,)
    transport.submit(submission=_submission(tenant="globex"))
    assert transport.submissions(tenant="acme-bank") == ()


# --- the Protocol seam --------------------------------------------------------


def test_the_reference_impl_satisfies_the_protocol() -> None:
    assert isinstance(InMemoryHitlTransport(), HITLTransportProtocol)


def test_the_module_records_the_d_impl_20_separation() -> None:
    import ccf.hitl.transport as module

    assert module.__doc__ is not None
    assert "notify-only" in module.__doc__
    assert "07-08" in module.__doc__
