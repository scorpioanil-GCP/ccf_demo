"""``OverrideBoundary`` — the typed substitution HITL primitive (07-08).

Written before the implementation per the TDD discipline. The claims:

An override records the original agent output AND the substituted value,
both canonically serialized, in the dimension-2 block — byte-assertable
(T-07-16); an override without a
:class:`~ccf.hitl.principal.HumanPrincipalBinding` is unrepresentable
through the typed contract, and the binding's ``product_content_hash``
must match what the overrider saw (TOCTOU); a declined override — the
human confirms the agent value — is also a recorded action, never an
absence; neither value is mutated in place; resolving an event the queue
does not hold raises (broken wiring, I.1 line).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import AuditLog
from ccf.hitl.override import (
    OverrideBoundary,
    OverrideResolution,
    OverrideResolutionRefused,
    UnknownOverrideEventError,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport

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
    fixture: dict[str, Any], *, product_content_hash: str
) -> HumanPrincipalBinding:
    approver = fixture["approvers"]["credit_officer"]
    return HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _boundary() -> tuple[
    OverrideBoundary[_Determination], InMemoryHitlTransport, AuditLog
]:
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    boundary: OverrideBoundary[_Determination] = OverrideBoundary(
        transport=transport, audit=audit, clock=_clock()
    )
    return boundary, transport, audit


def _propose(
    boundary: OverrideBoundary[_Determination], fixture: dict[str, Any]
) -> _Determination:
    document = fixture["override"]["event"]
    original = _Determination(**fixture["override"]["original"])
    boundary.propose(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        original=original,
        policy_ref=document["policy_ref"],
    )
    return original


def test_an_override_records_both_values_byte_assertably() -> None:
    """Original AND substitute land canonically serialized in the dim-2
    block (T-07-16 mitigation), and neither is mutated in place."""
    fixture = _hitl()
    boundary, transport, audit = _boundary()
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    substitute = _Determination(**fixture["override"]["substitute"])
    resolution = boundary.resolve(
        tenant=document["tenant"],
        event_key=document["event_key"],
        principal=_principal(
            fixture, product_content_hash=content_hash(original)
        ),
        override=substitute,
    )
    assert isinstance(resolution, OverrideResolution)
    assert resolution.record.overridden
    assert resolution.record.original == original
    assert resolution.record.final == substitute
    block = resolution.hitl_actions_block
    assert block == canonical_bytes(resolution.record).decode("utf-8")
    assert canonical_bytes(original).decode("utf-8") in block
    assert canonical_bytes(substitute).decode("utf-8") in block
    # Preserved verbatim: the inputs still equal their fixture values.
    assert original == _Determination(**fixture["override"]["original"])
    assert substitute == _Determination(**fixture["override"]["substitute"])
    (submission,) = transport.submissions(tenant=document["tenant"])
    assert submission.action == "override"
    events = audit.events()
    assert events[-1].action == "hitl_action" and events[-1].resolved


def test_an_unbound_override_is_unrepresentable() -> None:
    """The typed transport contract requires the principal by type (D-22
    type-unrepresentable leg)."""
    fixture = _hitl()
    document = fixture["override"]["event"]
    with pytest.raises(ValidationError):
        HitlActionSubmission(  # type: ignore[call-arg]
            event_key=document["event_key"],
            tenant=document["tenant"],
            action="override",
        )


def test_a_hash_mismatch_is_refused_and_the_event_stays_pending() -> None:
    """The binding's product_content_hash must name what the overrider
    actually saw; a mismatch is a typed refusal, audited resolved=False."""
    fixture = _hitl()
    boundary, transport, audit = _boundary()
    _propose(boundary, fixture)
    document = fixture["override"]["event"]
    stale = content_hash({"stale": "output"})
    refused = boundary.resolve(
        tenant=document["tenant"],
        event_key=document["event_key"],
        principal=_principal(fixture, product_content_hash=stale),
        override=_Determination(**fixture["override"]["substitute"]),
    )
    assert isinstance(refused, OverrideResolutionRefused)
    assert len(transport.pending(tenant=document["tenant"])) == 1
    events = audit.events()
    assert events[-1].action == "hitl_action" and not events[-1].resolved


def test_a_declined_override_is_a_recorded_action() -> None:
    """Confirming the agent value is an action, never an absence: recorded,
    audited, and on dimension 2 with overridden=False."""
    fixture = _hitl()
    boundary, transport, audit = _boundary()
    original = _propose(boundary, fixture)
    document = fixture["override"]["event"]
    resolution = boundary.resolve(
        tenant=document["tenant"],
        event_key=document["event_key"],
        principal=_principal(
            fixture, product_content_hash=content_hash(original)
        ),
        override=None,
    )
    assert isinstance(resolution, OverrideResolution)
    assert not resolution.record.overridden
    assert resolution.record.original == original
    assert resolution.record.final == original
    assert resolution.hitl_actions_block == canonical_bytes(
        resolution.record
    ).decode("utf-8")
    (submission,) = transport.submissions(tenant=document["tenant"])
    assert submission.action == "approve"
    events = audit.events()
    assert events[-1].action == "hitl_action" and events[-1].resolved


def test_resolving_an_unknown_event_raises() -> None:
    fixture = _hitl()
    boundary, _, _ = _boundary()
    document = fixture["override"]["event"]
    with pytest.raises(UnknownOverrideEventError):
        boundary.resolve(
            tenant=document["tenant"],
            event_key="acme-bank/exec-ovr/no-such-event",
            principal=_principal(
                fixture, product_content_hash=content_hash({"any": "thing"})
            ),
            override=None,
        )
