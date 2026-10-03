"""HITLTransportProtocol + in-memory reference impl (D-IMPL-20).

Written before the implementation per the TDD discipline. The claims pinned
here: the transport is a *typed* queue — extra=forbid contracts in, the
same contracts out, never dicts; the authority path requires a
:class:`~ccf.hitl.principal.HumanPrincipalBinding` **by type**, so an
unattributed action submission is unrepresentable through the contract; and
queue views are per-tenant — two tenants' queues never interleave (D-23).

Under D-IMPL-353 §1.2 the authority path takes the capability: ``submit``
requires an ``Authorized[HitlSubmit]`` for the event and files under its
tenant; the submission contract carries no tenant. The capability controls
proper live in ``test_transport_capability.py``; here every submit simply
presents the genuine capability for its own tenant and event.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.authz.capability import Authorized, HitlSubmit
from ccf.hitl.transport import (
    HITL_ACTIONS,
    HITL_EVENT_CLASSES,
    HitlActionSubmission,
    HITLTransportProtocol,
    InMemoryHitlTransport,
    PendingHitlEvent,
)

from .capabilities import submit_capability

ACTION_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
SUBJECT = "credit-officer-7"


def _binding() -> HumanPrincipalBinding:
    return HumanPrincipalBinding.model_validate(
        {
            "approver": {
                "subject_id": SUBJECT,
                "identity_provider_ref": "oidc:acme-bank-sso",
            },
            "authentication": {
                "method": "oidc",
                "assurance_level": "aal2",
                "session_ref": "session-01HZX",
            },
            "action_time": ACTION_TIME,
            "product_content_hash": content_hash({"product": "seen"}),
            "verdict": "approve",
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
        "action": "approve",
        "principal": _binding(),
        "annotation": None,
    }
    document.update(mutations)
    return HitlActionSubmission.model_validate(document)


def _authorized(
    tenant: str = "acme-bank", event_key: str = "acme-bank/approvals/1"
) -> Authorized[HitlSubmit]:
    """The genuine capability for this tenant, event and subject."""
    return submit_capability(tenant=tenant, principal=SUBJECT, event_key=event_key)


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
    transport.submit(_authorized(), submission=submission)
    recorded = transport.submissions(tenant="acme-bank")
    # Equal up to the transport's own stamps — the decision id it recorded
    # is the capability's, never the caller's.
    assert recorded == (
        submission.model_copy(
            update={"authorizing_decision_id": _authorized().decision_id}
        ),
    )
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
    transport.submit(
        _authorized(tenant="globex", event_key="globex/approvals/1"),
        submission=_submission(event_key="globex/approvals/1"),
    )
    assert transport.submissions(tenant="acme-bank") == ()


# --- the Protocol seam --------------------------------------------------------


def test_the_reference_impl_satisfies_the_protocol() -> None:
    assert isinstance(InMemoryHitlTransport(), HITLTransportProtocol)


def test_the_module_records_the_d_impl_20_separation() -> None:
    import ccf.hitl.transport as module

    assert module.__doc__ is not None
    assert "notify-only" in module.__doc__
    assert "07-08" in module.__doc__


# --- the claim stamp: which pending event an action actually answered ---------
#
# SEC-001 Tier 0 (2026-09-24). A recorded submission used to say WHAT a human
# did and WHO they were, and nothing about WHICH pending event the action
# answered — so a consumer of the authority path (the workflow engine's
# gate-authority check) could not tell an approval-gate verdict from an
# escalation verdict that named the same event key. The transport now records
# its OWN observation of what was claimed. These tests pin that the stamp is
# the transport's statement and never the submitter's.


def test_a_claimed_event_stamps_the_submission_that_answers_it() -> None:
    """``remove`` is a claim; the next ``submit`` for that pair carries it."""
    transport = InMemoryHitlTransport()
    event = _event()
    transport.enqueue(event=event)
    assert transport.remove(tenant=event.tenant, event_key=event.event_key)
    transport.submit(_authorized(), submission=_submission())
    (recorded,) = transport.submissions(tenant=event.tenant)
    assert recorded.answered_event_class == event.event_class
    assert recorded.answered_workflow_state_ref == event.workflow_state_ref


def test_a_submission_that_claimed_nothing_carries_no_stamp() -> None:
    """The submit-only door's shape (D-IMPL-62): it resolves nothing, so
    nothing on the authority path says which primitive it answered."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    transport.submit(_authorized(), submission=_submission())
    (recorded,) = transport.submissions(tenant="acme-bank")
    assert recorded.answered_event_class is None
    assert recorded.answered_workflow_state_ref is None


def test_a_caller_supplied_stamp_is_discarded_rather_than_trusted() -> None:
    """The load-bearing property: the submitter cannot author the value the
    check compares. A guard whose input the caller supplies is not a guard
    (the lesson the first SEC-001 fix taught at cost).

    The fields are declared on the contract, so a caller CAN set them —
    which is why the transport overwrites both on every submit rather than
    only when it has something to write.
    """
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    transport.submit(
        _authorized(),
        submission=_submission(
            answered_event_class="approval-gate",
            answered_workflow_state_ref="workflow-state/anything-i-like",
        ),
    )
    (recorded,) = transport.submissions(tenant="acme-bank")
    assert recorded.answered_event_class is None
    assert recorded.answered_workflow_state_ref is None


def test_a_returned_claim_does_not_stamp_a_later_bare_submission() -> None:
    """The rollback path leaves no residue to inherit.

    Every shipped primitive claims before it submits and gives the claim
    back when the submit is refused (``remove`` -> failed ``submit`` ->
    ``enqueue``). If the claim outlived that give-back, the NEXT submission
    for the same event key — including one from the submit-only door, which
    claimed nothing — would inherit a stamp saying a primitive had answered
    it. Enqueue discards the claim, so it does not.
    """
    transport = InMemoryHitlTransport()
    event = _event()
    transport.enqueue(event=event)
    claimed = transport.remove(
        tenant=event.tenant, event_key=event.event_key
    )
    assert claimed is not None
    transport.enqueue(event=claimed)  # the give-back
    transport.submit(_authorized(), submission=_submission())
    (recorded,) = transport.submissions(tenant=event.tenant)
    assert recorded.answered_event_class is None
    assert recorded.answered_workflow_state_ref is None


def test_one_claim_stamps_one_submission() -> None:
    """A claim is consumed by the submission that answers it, so a second
    action against the same event key cannot re-use the first's authority."""
    transport = InMemoryHitlTransport()
    event = _event()
    transport.enqueue(event=event)
    assert transport.remove(tenant=event.tenant, event_key=event.event_key)
    transport.submit(_authorized(), submission=_submission())
    transport.submit(_authorized(), submission=_submission(action="reject"))
    first, second = transport.submissions(tenant=event.tenant)
    assert first.answered_event_class == event.event_class
    assert second.answered_event_class is None


def test_a_drained_event_is_not_a_claim() -> None:
    """``dequeue`` is a drain, not a resolution: it stamps nothing."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    assert transport.dequeue(tenant="acme-bank") is not None
    transport.submit(_authorized(), submission=_submission())
    (recorded,) = transport.submissions(tenant="acme-bank")
    assert recorded.answered_event_class is None


def test_a_claim_belongs_to_its_own_tenant_and_event_key() -> None:
    """D-23: one tenant's claim never stamps another's action, and a claim
    of one event never stamps an action against a different one."""
    transport = InMemoryHitlTransport()
    event = _event()
    transport.enqueue(event=event)
    assert transport.remove(tenant=event.tenant, event_key=event.event_key)
    other_key = "acme-bank/approvals/2"
    transport.submit(
        _authorized(tenant="harbor-credit"), submission=_submission()
    )
    transport.submit(
        _authorized(event_key=other_key), submission=_submission(event_key=other_key)
    )
    (across,) = transport.submissions(tenant="harbor-credit")
    (beside,) = transport.submissions(tenant="acme-bank")
    assert across.answered_event_class is None
    assert beside.answered_event_class is None
