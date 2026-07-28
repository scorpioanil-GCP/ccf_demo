"""The Control Plane's audit plane (whitepaper §7.8.2; INV-CH7-71).

The whitepaper does not give the Control Plane an audit *feature*; it says the
Control Plane **is** the audit plane. Every configuration change is versioned,
timestamped, and retained against the decisions made under it. This module is
that commitment in mechanism: a typed event contract and an append-only log,
separated from the registry so that the log is a thing a reviewer can read,
hand to another surface, or persist — rather than a private list inside one
class.

Three properties are load-bearing:

**Append-only.** :class:`AuditLog` exposes ``append`` and ``events`` and
nothing else. There is no delete, no truncate, no compaction and no mutable
view. An audit log that can be edited answers a different question than the one
an examiner asks (threat T-04-16).

**Failed interactions are recorded.** ``resolved=False`` events exist because a
log of successes cannot answer "what did this deployment ask for and not
have?" — which is exactly the question a fail-closed posture makes material.

**Time is injected.** Events carry the timestamp the registry's clock supplied.
No module here reads a wall clock, so an audit log replays.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = ["AuditAction", "AuditEvent", "AuditLog"]

#: The Control Plane interactions worth a record. Registration and resolution
#: are both here because the audit plane's obligation is to reconstruct *what
#: configuration a decision ran under*, which needs the reads as much as the
#: writes. The ``grant_*`` members are the skill-grant state transitions
#: (D-IMPL-29; D-09): a grant is a Control Plane action like any other, and
#: every transition — refusals included — is a record (CLAUDE.md §6.2:
#: "a skill grant or revocation is itself an audited Control Plane action").
#: The ``a2a_*`` members are the federation admission verdicts (D-IMPL-16;
#: :mod:`ccf.peering.admission`): admitting a peer's Context Product is a Control
#: Plane decision like any other, and a refusal that left no record would let
#: a rejected federation attempt be denied afterwards (T-06-43).
#:
#: ``skill_invoked`` is the remaining member added for I.3: an ``mcp`` dispatch
#: leaves this process and contacts a remote server, and none of the existing
#: members can express that — ``resolve`` is a Control Plane read and the
#: ``grant_*`` family are grant-state transitions, so recording an invocation
#: as either would make the log say something untrue. It goes through this one
#: log, on the one existing ``append``; there is no parallel audit surface.
AuditAction = Literal[
    "register",
    "register_typed",
    "register_versioned",
    "resolve",
    "resolve_latest",
    "grant_requested",
    "grant_pending_approval",
    "grant_effective",
    "grant_refused",
    "grant_revoked",
    "a2a_admitted",
    "a2a_admission_refused",
    "skill_invoked",
]


class AuditEvent(CCFContract):
    """One audit-plane record of a Control Plane interaction (INV-CH7-71).

    Attributes:
        sequence: Monotonic position in the log. Gaps are detectable; ordering
            does not depend on timestamp resolution.
        action: Which interaction occurred.
        key: The configuration key involved.
        version: The version involved, or the version requested when the
            resolution failed.
        resolved: Whether the interaction succeeded.
        occurred_at: Timestamp from the registry's injected clock.
        actor: Who performed the interaction, when the caller states it. The
            SDK does not synthesize an identity: an unattributed action
            recorded as if attributed is worse than one recorded as unknown
            (identity binding is D-IMPL-21).
        artifact_class: The artifact class this interaction concerned, for
            typed registrations. Present so the log answers "what *kind* of
            thing changed" without re-resolving the artifact.
    """

    sequence: int
    action: AuditAction
    key: str
    version: str
    resolved: bool
    occurred_at: datetime
    actor: str | None = None
    artifact_class: str | None = None


class AuditLog:
    """An append-only sequence of :class:`AuditEvent`.

    Assigns each event its own sequence number, so callers cannot mis-number
    the log and a reader can detect a gap. Deliberately not a contract: it is
    mutable-by-appending state, whereas contracts are values.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def __len__(self) -> int:
        return len(self._events)

    def append(
        self,
        *,
        action: AuditAction,
        key: str,
        version: str,
        resolved: bool,
        occurred_at: datetime,
        actor: str | None = None,
        artifact_class: str | None = None,
    ) -> AuditEvent:
        """Append one event and return it, sequence number assigned."""
        event = AuditEvent(
            sequence=len(self._events),
            action=action,
            key=key,
            version=version,
            resolved=resolved,
            occurred_at=occurred_at,
            actor=actor,
            artifact_class=artifact_class,
        )
        self._events.append(event)
        return event

    def events(self) -> tuple[AuditEvent, ...]:
        """Return every recorded event, oldest first.

        A tuple rather than the internal list: a caller holding the log must not
        be able to rewrite history through the reference it was handed.
        """
        return tuple(self._events)
