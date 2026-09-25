"""The audit contract under the HARD-04 authz extension (10-01 Tasks 1-2).

Two obligations live here:

**The A2 byte-pin (RESEARCH assumption A2; Pitfall 3).** The canonical bytes
of an :class:`~ccf.controlplane.audit.AuditEvent` that uses none of the new
authz fields are pinned by sha256 literal, written *before* the Task 2
contract change. Replay determinism hangs on these bytes: if the pin breaks,
the executor STOPs and surfaces per RESEARCH Open Q3 — the pin is never
adapted to make a diff green.

**The D-09/D-10 decision-tuple cases (Task 2).** An ``authz_decision`` allow
and deny both land in the one Control Plane audit log carrying the full
tuple: principal (``actor``), tenant (``key``), action (``authz_action_id``),
decision (``resolved``), matched pattern (``authz_matched_pattern`` or
``None``), artifact version (``version``), timestamp (``occurred_at``).

Every domain-shaped value below is test fixture vocabulary, meaningful
nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.audit import (
    AuditEvent,
    AuditLog,
    AuthzDecisionAuditEvent,
)

#: The canonical bytes of a fully-populated, no-authz-fields AuditEvent,
#: pinned before the 10-01 Task 2 audit-contract change (assumption A2).
#: Computed over the event constructed in the test below. If this literal
#: ever needs editing, that is a STOP-and-surface event, not a test fix
#: (RESEARCH Open Q3; Pitfall 3).
A2_PINNED_SHA256 = (
    "cad994f692d08dba8923f921377510979439d637b60974747c97a3c911ac8d3a"
)


def _representative_event() -> AuditEvent:
    """One AuditEvent with every pre-Task-2 field populated."""
    return AuditEvent(
        sequence=7,
        action="resolve_latest",
        key="spike/audit-pin",
        version="1.2.3",
        resolved=True,
        occurred_at=datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC),
        actor="spike-actor",
        artifact_class="ccf.spike-class",
    )


def test_a2_no_new_fields_event_bytes_are_pinned() -> None:
    """A2: an AuditEvent using no authz fields serializes byte-identically
    before and after the authz audit extension."""
    digest = hashlib.sha256(canonical_bytes(_representative_event()))
    assert digest.hexdigest() == A2_PINNED_SHA256


def test_the_pin_covers_the_exact_canonical_form() -> None:
    """The pinned digest is over the canonical serializer's own bytes —
    the same serializer the replay pins use — not a hand-rolled rendering."""
    body = canonical_bytes(_representative_event()).decode("utf-8")
    # Spot-check the load-bearing properties of the canonical form so a
    # serializer change surfaces as a readable diff, not just a hash flip.
    assert body.startswith('{"action":"resolve_latest"')
    assert '"occurred_at":"2026-08-01T12:00:00.000000Z"' in body


def test_append_still_accepts_the_pre_extension_signature() -> None:
    """Task 2 is additive: the existing append call shape is untouched."""
    log = AuditLog()
    event = log.append(
        action="resolve_latest",
        key="spike/audit-pin",
        version="1.2.3",
        resolved=True,
        occurred_at=datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC),
        actor="spike-actor",
        artifact_class="ccf.spike-class",
    )
    assert event.sequence == 0
    assert log.events() == (event,)
    # The byte-stability leg of A2, stated directly: an append that names no
    # authz field yields an event whose canonical form carries no authz key.
    body = canonical_bytes(event).decode("utf-8")
    assert "authz_action_id" not in body
    assert "authz_matched_pattern" not in body


def test_an_authz_allow_carries_the_full_decision_tuple() -> None:
    """D-09/D-10: an allow lands as one ``authz_decision`` event carrying
    principal (actor), tenant (key), action, decision, matched pattern,
    artifact version, timestamp."""
    log = AuditLog()
    event = log.append(
        action="authz_decision",
        key="tenant-a",
        version="2.0.0",
        resolved=True,
        occurred_at=datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC),
        actor="caller-1",
        artifact_class="ccf.scope-mapping",
        authz_action_id="hitl.queue.read",
        authz_matched_pattern="tenant-*",
    )
    assert event.action == "authz_decision"
    assert event.resolved is True
    assert event.authz_action_id == "hitl.queue.read"
    assert event.authz_matched_pattern == "tenant-*"
    (read_back,) = log.events()
    assert read_back == event


def test_an_authz_deny_is_recorded_with_no_matched_pattern() -> None:
    """D-10: refusals are security-relevant events — a deny is the same
    member with ``resolved=False`` and no matched pattern."""
    log = AuditLog()
    event = log.append(
        action="authz_decision",
        key="tenant-b",
        version="2.0.0",
        resolved=False,
        occurred_at=datetime(2026, 8, 1, 12, 0, 1, tzinfo=UTC),
        actor="caller-1",
        artifact_class="ccf.scope-mapping",
        authz_action_id="hitl.action.submit",
        authz_matched_pattern=None,
    )
    assert event.resolved is False
    assert event.authz_action_id == "hitl.action.submit"
    assert event.authz_matched_pattern is None
    (read_back,) = log.events()
    assert read_back == event


def test_authz_events_and_plain_events_share_one_log_sequence() -> None:
    """D-11 (as read for this phase): authz decisions are standalone events
    in the SAME Control Plane audit log — one monotonic sequence, no
    separate surface (WR-07)."""
    log = AuditLog()
    plain = log.append(
        action="resolve_latest",
        key="authz/scope-mapping",
        version="2.0.0",
        resolved=True,
        occurred_at=datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC),
    )
    decision = log.append(
        action="authz_decision",
        key="tenant-a",
        version="2.0.0",
        resolved=True,
        occurred_at=datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC),
        actor="caller-1",
        authz_action_id="hitl.queue.read",
        authz_matched_pattern="tenant-a",
    )
    assert (plain.sequence, decision.sequence) == (0, 1)
    assert log.events() == (plain, decision)


# --- D-IMPL-353 §3: a deny says what it denied ------------------------------


def test_an_authz_event_carries_the_resource_and_the_failing_axis() -> None:
    """§3: ``resource``, the resource pattern that matched, and — on a deny —
    which axis refused. Three derived-class fields, so the A2 pin above is
    untouched: a plain event still renders none of them."""
    log = AuditLog()
    deny = log.append(
        action="authz_decision",
        key="tenant-b",
        version="2.0.0",
        resolved=False,
        occurred_at=datetime(2026, 8, 1, 12, 0, 1, tzinfo=UTC),
        actor="caller-1",
        artifact_class="ccf.scope-mapping",
        authz_action_id="config.register",
        authz_matched_pattern="tenant-*",
        authz_resource="prompts/underwriting",
        authz_matched_resource_pattern=None,
        authz_failing_axis="resource",
    )
    assert isinstance(deny, AuthzDecisionAuditEvent)
    assert deny.authz_resource == "prompts/underwriting"
    assert deny.authz_matched_resource_pattern is None
    assert deny.authz_failing_axis == "resource"
    allow = log.append(
        action="authz_decision",
        key="tenant-b",
        version="2.0.0",
        resolved=True,
        occurred_at=datetime(2026, 8, 1, 12, 0, 2, tzinfo=UTC),
        actor="caller-1",
        artifact_class="ccf.scope-mapping",
        authz_action_id="config.register",
        authz_matched_pattern="tenant-*",
        authz_resource="prompts/permitted",
        authz_matched_resource_pattern="prompts/*",
        authz_failing_axis=None,
    )
    assert isinstance(allow, AuthzDecisionAuditEvent)
    assert allow.authz_matched_resource_pattern == "prompts/*"
    assert allow.authz_failing_axis is None
    # The three new names render when SET, are absent at their sentinel
    # (hash-transparent, D-IMPL-243: an authz event appended before they
    # existed and one appended now with them at None are the same bytes),
    # and never appear on a plain event.
    plain = log.append(
        action="resolve",
        key="k",
        version="1",
        resolved=True,
        occurred_at=datetime(2026, 8, 1, 12, 0, 3, tzinfo=UTC),
    )
    plain_body = canonical_bytes(plain).decode("utf-8")
    deny_body = canonical_bytes(deny).decode("utf-8")
    allow_body = canonical_bytes(allow).decode("utf-8")
    for name in (
        "authz_resource",
        "authz_matched_resource_pattern",
        "authz_failing_axis",
    ):
        assert name not in plain_body
    assert "authz_resource" in deny_body and "authz_failing_axis" in deny_body
    assert "authz_matched_resource_pattern" not in deny_body  # None: silent
    assert "authz_matched_resource_pattern" in allow_body
    assert "authz_failing_axis" not in allow_body  # None on an allow: silent
    # And the bytes of an event that sets none of the three are exactly the
    # bytes of the same event before the fields existed.
    legacy = log.append(
        action="authz_decision",
        key="tenant-c",
        version="2.0.0",
        resolved=True,
        occurred_at=datetime(2026, 8, 1, 12, 0, 4, tzinfo=UTC),
        actor="caller-1",
        artifact_class="ccf.scope-mapping",
        authz_action_id="hitl.queue.read",
        authz_matched_pattern="tenant-*",
    )
    assert canonical_bytes(legacy).decode("utf-8") == (
        '{"action":"authz_decision","actor":"caller-1",'
        '"artifact_class":"ccf.scope-mapping","authz_action_id":"hitl.queue.read",'
        '"authz_matched_pattern":"tenant-*","key":"tenant-c",'
        '"occurred_at":"2026-08-01T12:00:04.000000Z","resolved":true,'
        '"sequence":3,"version":"2.0.0"}'
    )


def test_the_failing_axis_vocabulary_is_closed() -> None:
    """``tenant | action | resource | mapping`` and nothing else. ``mapping``
    exists because a deny with no resolvable scope mapping failed on NO axis,
    and recording it as one of the other three would be a lie about why."""
    from typing import get_args

    from ccf.controlplane.audit import AuthzFailingAxis

    assert set(get_args(AuthzFailingAxis)) == {
        "tenant",
        "action",
        "resource",
        "mapping",
    }
    with pytest.raises(ValidationError):
        AuthzDecisionAuditEvent(
            sequence=0,
            action="authz_decision",
            key="t",
            version="1",
            resolved=False,
            occurred_at=datetime(2026, 8, 1, tzinfo=UTC),
            authz_failing_axis="somewhere-else",  # type: ignore[arg-type]
        )
