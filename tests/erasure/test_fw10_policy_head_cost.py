"""FW-10 (whole-branch review M-5): ``policy_head`` does not copy and scan the audit log (SEC-009; `D-IMPL-374`).

``policy_head`` — the digest of the Control Plane's registration history that
keys the erasure verdict memo — is computed on every read of an erased address
and every composition. It copied the WHOLE audit log under the log's lock (the
lock every request's append also takes) and scanned it for registrations: the
review measured 0.3 ms at 10k events, 2.7 ms at 100k and 13 ms at 400k, linear,
on a server that appends an ``authz_decision`` per request — so each erased
read slowed with uptime and blocked appends.

Held here on the number of audit events read, never on time: the head is read
without reading the events that are not registrations, so its cost does not
grow with them; and its VALUE is still the digest of the registration history —
it moves on a registration and on nothing else.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure.approval import policy_head
from tests.composition import register_at_composition

INSTANT = datetime(2026, 8, 1, tzinfo=UTC)


class _CountingLog:
    """The registry's audit log, counting every event a reader is handed."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.read = 0

    def events(self) -> tuple[Any, ...]:
        events = self._inner.events()
        self.read += len(events)
        return events

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _CountingPlane:
    """A Control Plane whose audit reads are counted, however they are made."""

    def __init__(self, inner: ControlPlaneRegistry) -> None:
        self._inner = inner
        self.audit_log = _CountingLog(inner.audit_log)

    def audit_events(self) -> tuple[Any, ...]:
        return self.audit_log.events()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _unrelated(registry: ControlPlaneRegistry, count: int) -> None:
    """Audit events that are not registrations: what a serving door appends per request."""
    for index in range(count):
        registry.audit_log.append(
            action="resolve", key=f"fw10/unrelated/{index}", version="1.0.0", resolved=True, occurred_at=INSTANT
        )


def _events_read(unrelated: int) -> tuple[int, str]:
    registry = ControlPlaneRegistry()
    register_at_composition(registry, "fw10/policy", {"regime": "fw-10"})
    _unrelated(registry, unrelated)
    plane = _CountingPlane(registry)
    head = policy_head(plane)  # type: ignore[arg-type]
    return plane.audit_log.read, head


def test_fw10_the_head_reads_no_more_events_as_unrelated_events_accumulate() -> None:
    small_read, _small_head = _events_read(10)
    large_read, _large_head = _events_read(2_000)
    assert large_read == small_read, (
        f"policy_head read {small_read} audit events beside 10 unrelated ones and"
        f" {large_read} beside 2000: its cost grows with the audit log"
    )
    # (The two heads come from two registries whose registrations carry their
    # own instants, so they are not compared; the companion test holds the
    # value within one registry.)


def test_fw10_the_head_is_still_the_registration_history_digest() -> None:
    registry = ControlPlaneRegistry()
    register_at_composition(registry, "fw10/policy", {"regime": "fw-10"})
    _unrelated(registry, 5)
    expected = hashlib.sha256()
    for event in registry.audit_log.events():
        if event.action in {"register", "register_typed", "register_versioned"} and event.resolved:
            expected.update(
                f"{event.action}\x1f{event.key}\x1f{event.version}\x1f{event.occurred_at.isoformat()}\x1e".encode()
            )
    before = policy_head(registry)
    assert before == expected.hexdigest()
    _unrelated(registry, 5)
    assert policy_head(registry) == before, "an unrelated event moved the head"
    register_at_composition(registry, "fw10/policy-2", {"regime": "fw-10-b"})
    assert policy_head(registry) != before, "a registration did not move the head"
