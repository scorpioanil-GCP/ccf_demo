"""Notify-only webhook HITL transport (D-IMPL-64; D-IMPL-20).

Written before the implementation per the TDD discipline. The claims:

**Notify-only by construction.** The notification payload carries the
pending event and nothing that could act on it — no action field, no
principal, no submit surface; the notifier module never imports the
action-submission contract and the notifier object exposes no ``submit``.
Authority always returns through the typed
:class:`~ccf.hitl.transport.HITLTransportProtocol` queue (D-IMPL-20).

**Injected delivery seam.** How bytes reach an endpoint is the
deployment's infrastructure — the deliverer is an injected Protocol; a
recording in-memory reference ships alongside it (CLAUDE.md §11).

**Failure is recorded, never raised into the authority path.** A failing
endpoint yields a typed outcome with ``delivered=False`` and the error
text; other endpoints still receive their notification.

**Tenant isolation (D-23).** An event notifies only the endpoints
registered for its tenant.

**Typed refusals.** A duplicate endpoint key at construction is a typed
refusal, not a silent overwrite; an extra field on any contract dies at
the boundary.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.hitl.transport import PendingHitlEvent
from ccf.hitl.webhook import (
    HitlEventNotification,
    RecordingWebhookDeliverer,
    WebhookDeliveryOutcome,
    WebhookDeliveryProtocol,
    WebhookEndpoint,
    WebhookEndpointConflict,
    WebhookHitlNotifier,
)


def _event(tenant: str = "acme-bank", key: str = "1") -> PendingHitlEvent:
    return PendingHitlEvent(
        event_key=f"{tenant}/approvals/{key}",
        event_class="approval-gate",
        tenant=tenant,
        workflow_state_ref="workflow-state/covenant-review/run-1",
        product_content_hash=content_hash({"product": "seen"}),
    )


def _endpoint(
    key: str, tenant: str = "acme-bank", url: str = "https://hooks.invalid/a"
) -> WebhookEndpoint:
    return WebhookEndpoint(endpoint_key=key, tenant=tenant, url=url)


# --- delivery and tenant isolation ------------------------------------------


def test_an_event_notifies_every_endpoint_of_its_tenant_only() -> None:
    deliverer = RecordingWebhookDeliverer()
    notifier = WebhookHitlNotifier(
        deliverer=deliverer,
        endpoints=(
            _endpoint("ops-a"),
            _endpoint("ops-b", url="https://hooks.invalid/b"),
            _endpoint("other", tenant="zenith-fund"),
        ),
    )
    outcomes = notifier.notify(event=_event())
    assert [o.endpoint_key for o in outcomes] == ["ops-a", "ops-b"]
    assert all(o.delivered and o.error is None for o in outcomes)
    delivered_urls = [url for url, _ in deliverer.deliveries]
    assert delivered_urls == [
        "https://hooks.invalid/a",
        "https://hooks.invalid/b",
    ]
    for _, notification in deliverer.deliveries:
        assert isinstance(notification, HitlEventNotification)
        assert notification.event == _event()


def test_a_tenant_with_no_endpoints_yields_no_outcomes() -> None:
    deliverer = RecordingWebhookDeliverer()
    notifier = WebhookHitlNotifier(
        deliverer=deliverer, endpoints=(_endpoint("ops-a"),)
    )
    assert notifier.notify(event=_event(tenant="zenith-fund")) == ()
    assert deliverer.deliveries == []


# --- failure is recorded, never raised --------------------------------------


class _FailingDeliverer:
    def __init__(self, failing_url: str) -> None:
        self.failing_url = failing_url
        self.deliveries: list[tuple[str, HitlEventNotification]] = []

    def deliver(
        self, *, url: str, notification: HitlEventNotification
    ) -> None:
        if url == self.failing_url:
            raise RuntimeError("endpoint unreachable")
        self.deliveries.append((url, notification))


def test_a_failing_endpoint_is_a_recorded_outcome_not_an_exception() -> None:
    deliverer = _FailingDeliverer(failing_url="https://hooks.invalid/a")
    notifier = WebhookHitlNotifier(
        deliverer=deliverer,
        endpoints=(
            _endpoint("ops-a"),
            _endpoint("ops-b", url="https://hooks.invalid/b"),
        ),
    )
    outcomes = notifier.notify(event=_event())
    assert isinstance(outcomes[0], WebhookDeliveryOutcome)
    assert outcomes[0].delivered is False
    assert outcomes[0].error is not None
    assert "endpoint unreachable" in outcomes[0].error
    # the other endpoint still received its notification
    assert outcomes[1].delivered is True
    assert [url for url, _ in deliverer.deliveries] == [
        "https://hooks.invalid/b"
    ]


# --- typed refusals ----------------------------------------------------------


def test_duplicate_endpoint_keys_are_a_typed_refusal() -> None:
    with pytest.raises(WebhookEndpointConflict):
        WebhookHitlNotifier(
            deliverer=RecordingWebhookDeliverer(),
            endpoints=(_endpoint("ops-a"), _endpoint("ops-a")),
        )


@pytest.mark.parametrize(
    "contract, document",
    [
        (
            WebhookEndpoint,
            {
                "endpoint_key": "k",
                "tenant": "t",
                "url": "https://hooks.invalid",
                "extra": True,
            },
        ),
        (
            HitlEventNotification,
            {
                "endpoint_key": "k",
                "event": _event().model_dump(),
                "extra": True,
            },
        ),
    ],
)
def test_an_extra_field_dies_at_the_boundary(
    contract: Any, document: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError):
        contract.model_validate(document)


# --- notify-only by construction --------------------------------------------


def test_the_notification_carries_no_authority_surface() -> None:
    fields = set(HitlEventNotification.model_fields)
    assert fields == {"endpoint_key", "event"}
    assert "action" not in fields and "principal" not in fields


def test_the_webhook_module_has_no_submit_path() -> None:
    import ccf.hitl.webhook as webhook

    source = inspect.getsource(webhook)
    assert "HitlActionSubmission" not in source
    assert ".submit(" not in source
    assert not hasattr(
        WebhookHitlNotifier(
            deliverer=RecordingWebhookDeliverer(), endpoints=()
        ),
        "submit",
    )


def test_the_deliverer_seam_is_a_protocol() -> None:
    assert isinstance(RecordingWebhookDeliverer(), WebhookDeliveryProtocol)
