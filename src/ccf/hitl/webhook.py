"""The notify-only webhook HITL transport (D-IMPL-64; D-IMPL-20).

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so). D-IMPL-20 rules two reference transports and separates
notification from authority; D-IMPL-64 (Dave, 2026-07-30) rules the
notify-only webhook emitter into v0. **Notify-only means structural,
not advisory:** this module notifies external systems that a HITL event is
pending — nothing more. The notification payload carries the typed
:class:`~ccf.hitl.transport.PendingHitlEvent` and no action, no principal,
and no submit surface; a human acting on a notification returns through
the typed :class:`~ccf.hitl.transport.HITLTransportProtocol` queue, so
audit-by-construction cannot be bypassed from a notification channel.

**Delivery is the deployment's infrastructure.** How bytes reach an
endpoint — HTTP client, signing, retry policy — is deliberately outside
the SDK (the 07-08 rationale D-IMPL-64 preserves): the
:class:`WebhookDeliveryProtocol` seam is injected, and
:class:`RecordingWebhookDeliverer` ships as the in-memory reference
implementation per CLAUDE.md §11. Endpoint registrations are typed,
caller-supplied values — Control Plane artifacts in a deployment, never
constants here (No-Hardcoding, §6.4).

**A failed notification is recorded, never raised into the authority
path.** Notification is an observer; an unreachable endpoint yields a
typed :class:`WebhookDeliveryOutcome` with the error text, and the other
endpoints still receive theirs.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.hitl.transport import PendingHitlEvent

__ccf_mode__ = "algorithmic"

__all__ = [
    "HitlEventNotification",
    "RecordingWebhookDeliverer",
    "WebhookDeliveryOutcome",
    "WebhookDeliveryProtocol",
    "WebhookEndpoint",
    "WebhookEndpointConflict",
    "WebhookHitlNotifier",
]


class WebhookEndpointConflict(ValueError):
    """Typed refusal: two endpoint registrations share one key."""


class WebhookEndpoint(CCFContract):
    """One registered notification endpoint (D-IMPL-64).

    SDK-defined. A typed, caller-supplied registration — in a deployment
    these come from Control Plane configuration, never from constants in
    code (No-Hardcoding, CLAUDE.md §6.4). ``tenant`` scopes delivery:
    an event notifies only its own tenant's endpoints (D-23).
    """

    endpoint_key: str
    tenant: str
    url: str


class HitlEventNotification(CCFContract):
    """The notify-only payload (D-IMPL-64).

    SDK-defined. Deliberately carries the pending event and the endpoint
    key — and nothing that could act: no action field, no principal, no
    reference to the submission contract. Authority returns through the
    typed queue (D-IMPL-20), never through this payload.
    """

    endpoint_key: str
    event: PendingHitlEvent


class WebhookDeliveryOutcome(CCFContract):
    """One delivery attempt's recorded disposition (D-IMPL-64).

    SDK-defined. ``delivered=False`` with the error text is the honest
    record of an unreachable endpoint — notification failure is recorded,
    never raised into the authority path.
    """

    endpoint_key: str
    delivered: bool
    error: str | None = None


@runtime_checkable
class WebhookDeliveryProtocol(Protocol):
    """The injected delivery seam (D-IMPL-64; CLAUDE.md §11).

    A Protocol because transport mechanics — HTTP client choice, signing,
    retries, endpoint authentication — are notification-infrastructure
    choices the SDK has no business making (the 07-08 rationale the
    D-IMPL-64 ruling preserves). ``runtime_checkable`` supports
    composition-root wiring checks; static conformance rests on mypy.
    """

    def deliver(
        self, *, url: str, notification: HitlEventNotification
    ) -> None:
        """Deliver ``notification`` to ``url``; raise on failure."""
        ...


class RecordingWebhookDeliverer:
    """In-process reference implementation of :class:`WebhookDeliveryProtocol`.

    Ships alongside the Protocol per CLAUDE.md §11 — a reference
    implementation, not a placeholder for one: it records each delivery
    in order, which is exactly the observable a composition root or a
    test needs from a notification observer with no network.
    """

    def __init__(self) -> None:
        self.deliveries: list[tuple[str, HitlEventNotification]] = []

    def deliver(
        self, *, url: str, notification: HitlEventNotification
    ) -> None:
        """Record the delivery in arrival order."""
        self.deliveries.append((url, notification))


class WebhookHitlNotifier:
    """The notify-only emitter over registered endpoints (D-IMPL-64).

    A pure observer of pending HITL events: :meth:`notify` renders one
    typed :class:`HitlEventNotification` per endpoint registered for the
    event's tenant and hands each to the injected deliverer. There is no
    submit path on this object, by construction — it holds no transport
    handle and imports no submission contract.
    """

    def __init__(
        self,
        *,
        deliverer: WebhookDeliveryProtocol,
        endpoints: tuple[WebhookEndpoint, ...],
    ) -> None:
        keys = [endpoint.endpoint_key for endpoint in endpoints]
        duplicates = {key for key in keys if keys.count(key) > 1}
        if duplicates:
            raise WebhookEndpointConflict(
                f"duplicate webhook endpoint keys {sorted(duplicates)};"
                " each registration must carry its own key (D-IMPL-64)"
            )
        self._deliverer = deliverer
        self._endpoints = endpoints

    def notify(
        self, *, event: PendingHitlEvent
    ) -> tuple[WebhookDeliveryOutcome, ...]:
        """Notify the event's tenant's endpoints; record each disposition."""
        outcomes: list[WebhookDeliveryOutcome] = []
        for endpoint in self._endpoints:
            if endpoint.tenant != event.tenant:
                continue
            notification = HitlEventNotification(
                endpoint_key=endpoint.endpoint_key, event=event
            )
            try:
                self._deliverer.deliver(
                    url=endpoint.url, notification=notification
                )
            except Exception as error:  # noqa: BLE001 — recorded, not raised
                outcomes.append(
                    WebhookDeliveryOutcome(
                        endpoint_key=endpoint.endpoint_key,
                        delivered=False,
                        error=f"{type(error).__name__}: {error}",
                    )
                )
            else:
                outcomes.append(
                    WebhookDeliveryOutcome(
                        endpoint_key=endpoint.endpoint_key, delivered=True
                    )
                )
        return tuple(outcomes)
