"""The transport handle requires the capability for ITS action (D-IMPL-353 §1.2, §2 P6, §9).

Written before the transport took ``authorized``. Each control is one §9
clause at :meth:`~ccf.hitl.transport.HITLTransportProtocol.submit` and
:meth:`~ccf.hitl.transport.HITLTransportProtocol.view`:

* **wrong kind** — a genuine ``Authorized[HitlQueueRead]`` handed to
  ``submit`` dies at :func:`~ccf.authz.capability.verify` before
  anything is recorded (the runtime tooth; the static tooth for the same
  call is measured by ``test_capability_static.py``);
* **wrong resource, right kind** — a submit capability minted for event E,
  used on event F, dies the same way;
* **positive** — the right kind on its own event records
  ``authorized.principal`` as the actor, files under ``authorized.tenant``
  and stamps the decision id the capability is evidence of;
* **fabrication** — a ``Mock``, an ``object()``, a subclass that skipped
  ``__init__`` and a forged mint tuple all die at both handles;
* **no second source** — a binding over some other subject binds nothing
  here, and a caller-authored decision id is discarded.

Every "nothing recorded" assertion reads the transport back through the
in-process ``submissions``/``pending`` views, so a refusal that recorded
anyway would be visible.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import Mock

import pytest

from ccf.contracts.canonical import content_hash
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.hitl.transport import (
    HitlActionSubmission,
    InMemoryHitlTransport,
    PendingHitlEvent,
    PrincipalMismatchRefused,
)
from ccf.authz.capability import (
    Authorized,
    CapabilityBypassError,
    HitlQueueRead,
    HitlSubmit,
)

from .capabilities import queue_read_capability, submit_capability

TENANT = "acme-bank"
OTHER_TENANT = "harbor-credit"
PRINCIPAL = "credit-officer-7"
EVENT_E = "acme-bank/approvals/e"
EVENT_F = "acme-bank/approvals/f"
ACTION_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
PRODUCT_HASH = content_hash({"product": "seen"})


def _binding(subject_id: str = PRINCIPAL) -> HumanPrincipalBinding:
    return HumanPrincipalBinding.model_validate(
        {
            "approver": {
                "subject_id": subject_id,
                "identity_provider_ref": "oidc:acme-bank-sso",
            },
            "authentication": {
                "method": "oidc",
                "assurance_level": "aal2",
                "session_ref": "session-01HZX",
            },
            "action_time": ACTION_TIME,
            "product_content_hash": PRODUCT_HASH,
        }
    )


def _event(*, event_key: str = EVENT_E, tenant: str = TENANT) -> PendingHitlEvent:
    return PendingHitlEvent(
        event_key=event_key,
        event_class="approval-gate",
        tenant=tenant,
        workflow_state_ref=f"{tenant}/exec-1",
        product_content_hash=PRODUCT_HASH,
    )


def _submission(
    *, event_key: str = EVENT_E, subject_id: str = PRINCIPAL, **extra: Any
) -> HitlActionSubmission:
    return HitlActionSubmission(
        event_key=event_key,
        action="approve",
        principal=_binding(subject_id),
        **extra,
    )


def _submit_cap(event_key: str = EVENT_E, tenant: str = TENANT) -> Authorized[HitlSubmit]:
    return submit_capability(tenant=tenant, principal=PRINCIPAL, event_key=event_key)


def _nothing_recorded(transport: InMemoryHitlTransport) -> None:
    assert transport.submissions(tenant=TENANT) == ()
    assert transport.submissions(tenant=OTHER_TENANT) == ()


# --- §9 negative control: wrong kind ---------------------------------------


def test_a_queue_read_capability_handed_to_submit_dies_wrong_kind() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    assert transport.remove(tenant=TENANT, event_key=EVENT_E) is not None
    read = queue_read_capability(tenant=TENANT, principal=PRINCIPAL, resource=EVENT_E)
    with pytest.raises(CapabilityBypassError, match="kind"):
        # The runtime half: forced past the static tooth through `object`.
        transport.submit(read, submission=_submission())  # type: ignore[arg-type]
    _nothing_recorded(transport)
    # The claim the primitive holds is untouched by a refused submit: the
    # next genuine submit still carries it.
    recorded = transport.submit(_submit_cap(), submission=_submission())
    assert recorded.answered_event_class == "approval-gate"


def test_a_submit_capability_handed_to_view_dies_wrong_kind() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    with pytest.raises(CapabilityBypassError, match="kind"):
        transport.view(_submit_cap())  # type: ignore[arg-type]


# --- §9 negative control: wrong resource, right kind -----------------------


def test_a_submit_capability_for_event_e_used_on_event_f_dies_wrong_resource() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event(event_key=EVENT_F))
    with pytest.raises(CapabilityBypassError, match="resource"):
        transport.submit(_submit_cap(EVENT_E), submission=_submission(event_key=EVENT_F))
    _nothing_recorded(transport)
    assert transport.pending(tenant=TENANT) == (_event(event_key=EVENT_F),)


def test_a_queue_read_capability_for_another_resource_dies_at_view() -> None:
    """A queue read is addressed by tenant alone, so its one honest resource is
    the door's own action id (ROUTE semantics). A read capability minted for
    anything else is not this read."""
    transport = InMemoryHitlTransport()
    elsewhere = queue_read_capability(
        tenant=TENANT, principal=PRINCIPAL, resource="some-other-door"
    )
    with pytest.raises(CapabilityBypassError, match="resource"):
        transport.view(elsewhere)


# --- §9 positive control -----------------------------------------------------


def test_the_right_kind_on_its_own_event_records_the_principal_and_tenant() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    capability = _submit_cap()
    recorded = transport.submit(capability, submission=_submission())
    # Filed under the capability's tenant, and nowhere else.
    assert transport.submissions(tenant=TENANT) == (recorded,)
    assert transport.submissions(tenant=OTHER_TENANT) == ()
    # The actor IS the capability's principal.
    assert recorded.principal.approver.subject_id == capability.principal
    # And the record names the decision that authorized it.
    assert recorded.authorizing_decision_id == capability.decision_id
    assert recorded.authorizing_decision_id is not None


def test_submit_returns_the_recorded_copy_not_the_callers() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    assert transport.remove(tenant=TENANT, event_key=EVENT_E) is not None
    submitted = _submission()
    recorded = transport.submit(_submit_cap(), submission=submitted)
    assert recorded is not submitted
    assert recorded.answered_event_class == "approval-gate"
    assert submitted.answered_event_class is None  # frozen input, unmutated
    (stored,) = transport.submissions(tenant=TENANT)
    assert stored is recorded


def test_view_reads_the_capabilitys_tenant_and_only_that() -> None:
    transport = InMemoryHitlTransport()
    mine = _event(event_key=EVENT_E, tenant=TENANT)
    theirs = _event(event_key="harbor-credit/approvals/1", tenant=OTHER_TENANT)
    transport.enqueue(event=mine)
    transport.enqueue(event=theirs)
    read = queue_read_capability(tenant=TENANT, principal=PRINCIPAL)
    assert transport.view(read) == (mine,)
    other = queue_read_capability(tenant=OTHER_TENANT, principal=PRINCIPAL)
    assert transport.view(other) == (theirs,)


def test_the_tenant_on_the_record_is_the_capabilitys_whatever_the_event_says() -> None:
    """§1.3: there is no tenant anywhere in the submit path except the
    capability's. An event enqueued under another tenant with this key is
    simply not the event this capability's tenant claimed."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event(tenant=OTHER_TENANT))
    assert transport.remove(tenant=OTHER_TENANT, event_key=EVENT_E) is not None
    recorded = transport.submit(_submit_cap(tenant=TENANT), submission=_submission())
    assert transport.submissions(tenant=TENANT) == (recorded,)
    assert transport.submissions(tenant=OTHER_TENANT) == ()
    # The other tenant's claim was not consumed by this tenant's submit.
    assert recorded.answered_event_class is None


# --- no second source ------------------------------------------------------------


def test_a_binding_over_another_subject_than_the_principal_binds_nothing() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    with pytest.raises(PrincipalMismatchRefused, match="principal"):
        transport.submit(_submit_cap(), submission=_submission(subject_id="someone-else"))
    _nothing_recorded(transport)


def test_a_caller_authored_decision_id_is_discarded_rather_than_trusted() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    capability = _submit_cap()
    recorded = transport.submit(
        capability,
        submission=_submission(authorizing_decision_id="i-say-so"),
    )
    assert recorded.authorizing_decision_id == capability.decision_id
    assert recorded.authorizing_decision_id != "i-say-so"


# --- fabrication: dies at use, at both handles --------------------------------


def _forged() -> Any:
    forged = Authorized.__new__(Authorized)
    for name, value in (
        ("kind", HitlSubmit),
        ("tenant", TENANT),
        ("principal", PRINCIPAL),
        ("resource", EVENT_E),
        ("decision_id", "authz-decision-forged"),
        (
            "_minted",
            (object(), HitlSubmit, TENANT, PRINCIPAL, EVENT_E, "authz-decision-forged"),
        ),
    ):
        object.__setattr__(forged, name, value)
    return forged


def _mock() -> Any:
    fake = Mock()
    fake.kind, fake.tenant, fake.principal = HitlSubmit, TENANT, PRINCIPAL
    fake.resource, fake.decision_id = EVENT_E, "authz-decision-mock"
    return fake


@pytest.mark.parametrize(
    "fabricated",
    [_mock(), object(), Authorized.__new__(Authorized), _forged()],
    ids=["mock", "object", "subclass-skipping-init", "forged-mint-tuple"],
)
def test_every_fabrication_dies_at_submit_and_at_view(fabricated: Any) -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=_event())
    with pytest.raises(CapabilityBypassError):
        transport.submit(fabricated, submission=_submission())
    with pytest.raises(CapabilityBypassError):
        transport.view(fabricated)
    _nothing_recorded(transport)
    assert transport.pending(tenant=TENANT) == (_event(),)


def test_a_retargeted_genuine_capability_dies_at_submit() -> None:
    """§1.5(g) at this handle: a submit capability for E whose resource is
    forced to F is unusable for F AND for E."""
    capability = _submit_cap(EVENT_E)
    object.__setattr__(capability, "resource", EVENT_F)
    transport = InMemoryHitlTransport()
    with pytest.raises(CapabilityBypassError):
        transport.submit(capability, submission=_submission(event_key=EVENT_F))
    with pytest.raises(CapabilityBypassError):
        transport.submit(capability, submission=_submission(event_key=EVENT_E))
    _nothing_recorded(transport)


# --- the contract has no tenant --------------------------------------------------


def test_the_submission_contract_carries_no_tenant_field() -> None:
    """§1.3: deleted, not deprecated. A body that still sends one is refused
    by ``extra=forbid`` at the boundary, not silently dropped."""
    from pydantic import ValidationError

    assert "tenant" not in HitlActionSubmission.model_fields
    with pytest.raises(ValidationError, match="tenant"):
        HitlActionSubmission.model_validate(
            {
                "event_key": EVENT_E,
                "tenant": TENANT,
                "action": "approve",
                "principal": _binding(),
            }
        )
