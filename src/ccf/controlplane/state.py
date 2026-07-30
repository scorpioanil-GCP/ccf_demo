"""Mutable-until-terminal Control Plane state, behind one pluggable seam.

DESIGN.md §7; CLAUDE.md §10. D-IMPL-27 splits persistence **by mutability**:
immutable, versioned, replay-relevant artifacts route through the
ArtifactStore, while hot mutable state stays on native Protocols. This module
is that native surface for Control Plane state records — the state a governed
process mutates as it runs, and stops mutating when it reaches a terminal
outcome, at which point what is durable about it is the audit trail and the
replay record, never this store.

D-IMPL-18 named the substrate for suspended workflow execution state as "the
Control Plane's storage seam — pluggable there, no separate workflow-store
Protocol." This is that seam, declared once so every mutable-state consumer
shares it rather than minting a store apiece.

**What belongs here.** State that is mutable until terminal and whose
transitions are already audited: skill-grant state (``requested`` →
``pending-approval`` → ``effective`` / ``refused``, plus ``revoked``);
suspended workflow execution state when I.4 brings it. What does not: the
artifacts themselves. A grant *artifact* is immutable and registers
append-only into the versioned registry; only the grant's *state* lives here.
Confusing the two is the mutability rule failing (D-IMPL-27).

**Records are opaque.** The store keys and returns them without interpreting
them, so the state shapes belong to their consumers and this module holds no
vocabulary of its own — no grant states, no workflow states, no record schema
(CLAUDE.md §11, CINV-01). A consumer that needs a typed record defines it
next to the machine that transitions it.

**Why a seam rather than instance attributes.** State cached on the consuming
object diverges from every other consumer over the same Control Plane: two
:class:`~ccf.skills.grants.GrantLedger` instances over one registry
disagreed about which grants were effective, so a replay-facing
``grant_set_hash`` computed on a fresh ledger did not reproduce the skill-set
the decision was actually made under (WR-05; CLAUDE.md §6.2). Reading state
from the Control Plane instead of from the reader makes the disagreement
unrepresentable.

**Durability is the implementation's business, not the caller's.** The
reference implementation is in-process, matching the v0 Control Plane
posture (CLAUDE.md §13: an in-process versioned registry with an extension
point for remote control planes). A deployment needing state to survive a
restart supplies a conforming store; no consumer changes.

**Writes are audited by construction — D-22-scoped (07-02; D-20 closure).**
``put`` requires a :class:`StateWriteToken` that only this module mints, and
the only supported minting path is :class:`AuditedStateWriter`, which appends
the caller's domain :class:`~ccf.controlplane.audit.AuditEvent` to the one
existing :class:`~ccf.controlplane.audit.AuditLog` on every write
(INV-CH7-71: one audit plane, one event per write). An unaudited state write
is therefore unrepresentable **through the public write surface** — the
``put`` signature and the token's type contract are the enforcement. Bypass
via reflection or private construction (reaching for this module's private
sentinel, skipping ``__init__`` machinery) is not denied; it is out of the
claim's scope by design and is lint- and CI-covered instead (D-08, D-22).

**Reads remain unaudited, by scope of the same ruling.** ``get`` and
``items`` carry no token and append nothing: the closure governs *writes* —
what changed and on whose evidence — while read auditing stays where the
registry already draws that line (its ``resolve`` family). A reader can
enumerate state through ``items``; what it cannot do is change state without
leaving a record.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf.controlplane.audit import AuditEvent, AuditLog

__ccf_mode__ = "algorithmic"

__all__ = [
    "AuditedStateWriter",
    "ControlPlaneStateStore",
    "InMemoryStateStore",
    "StateWriteBypassError",
    "StateWriteToken",
]


class StateWriteBypassError(TypeError):
    """A state write was attempted outside the audited write path.

    The same discipline as
    :class:`~ccf.peering.admission.AdmissionBypassError`: the token type is
    constructible only inside this module, so holding one *is* the evidence
    the audited path ran (D-08; D-22-scoped — public write surface only).
    """


_STATE_WRITE_TOKEN = object()


class StateWriteToken:
    """Evidence that a state write travels the audited path (D-20 closure).

    Not constructible outside this module: the constructor demands the
    module-private sentinel, and :meth:`InMemoryStateStore.put` verifies the
    mint rather than trusting the type alone — a subclass that skips this
    ``__init__`` is refused at the write. The only supported producer is
    :class:`AuditedStateWriter`.

    D-22 scope: this makes an unaudited write unrepresentable through the
    *public write surface*; reflection and private-construction bypasses are
    lint- and CI-covered, never claimed impossible.
    """

    __slots__ = ("_minted",)

    def __init__(self, token: object) -> None:
        if token is not _STATE_WRITE_TOKEN:
            raise StateWriteBypassError(
                "StateWriteToken is minted only by"
                " ccf.controlplane.state.AuditedStateWriter; the audited"
                " write surface is the only path by which Control Plane"
                " state changes, so the write and its audit event are one"
                " action (INV-CH7-71; D-08; D-20 closure, 07-02)"
            )
        self._minted = _STATE_WRITE_TOKEN


def _verify(token: StateWriteToken) -> None:
    """Refuse a token this module did not mint (subclass/forgery guard)."""
    if getattr(token, "_minted", None) is not _STATE_WRITE_TOKEN:
        raise StateWriteBypassError(
            "the supplied token was not minted by"
            " ccf.controlplane.state.AuditedStateWriter; write Control Plane"
            " state through the audited surface (D-08; D-20 closure, 07-02)"
        )


@runtime_checkable
class ControlPlaneStateStore(Protocol):
    """The mutable-state surface a Control Plane must offer (D-IMPL-18/27).

    Records are addressed by ``(record_class, key)``. ``record_class``
    partitions the namespace so unrelated machines never collide on a shared
    key; it is an opaque identifier owned by the consuming module, exactly as
    :class:`~ccf.controlplane.artifacts.ArtifactClass` is for artifacts.

    Deliberately not append-only, unlike the registry: these records are
    mutable by definition, and their history lives in the audit log rather
    than in accumulated versions here. A store that versioned records would
    be answering a question D-IMPL-18 left to the durable implementation.
    """

    def get(self, record_class: str, key: str) -> object | None:
        """Return the record under ``key``, or ``None`` if there is none."""
        ...

    def put(
        self,
        record_class: str,
        key: str,
        record: object,
        *,
        token: StateWriteToken,
    ) -> None:
        """Write ``record`` under ``key``, replacing any prior record.

        ``token`` is the D-20 closure: only the audited write path
        (:class:`AuditedStateWriter`) mints one, so an implementation that
        honours this signature cannot be written to unaudited through the
        public write surface (D-22 scope).
        """
        ...

    def items(self, record_class: str) -> tuple[tuple[str, object], ...]:
        """Every ``(key, record)`` pair in one class, key-sorted.

        Sorted so callers that fold over the class — computing a set
        identity, listing what is in force — get an arrival-order-independent
        traversal, and a replay of the same state produces the same walk.
        """
        ...


class InMemoryStateStore:
    """In-process reference implementation of :class:`ControlPlaneStateStore`.

    Ships alongside the Protocol per CLAUDE.md §11, and is the v0 default:
    the Control Plane is itself in-process (CLAUDE.md §13), so state held here
    is exactly as durable as the registry and audit log beside it. It is the
    development and single-process implementation, not a placeholder for one —
    a durable store is an alternative implementation of the same Protocol,
    added without touching a consumer.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], object] = {}

    def get(self, record_class: str, key: str) -> object | None:
        """Return the record under ``key``, or ``None`` if there is none."""
        return self._records.get((record_class, key))

    def put(
        self,
        record_class: str,
        key: str,
        record: object,
        *,
        token: StateWriteToken,
    ) -> None:
        """Write ``record`` under ``key``, replacing any prior record.

        Verifies the token's mint rather than trusting its type: a subclass
        constructed around :class:`StateWriteToken.__init__` is refused here
        (D-22 public-surface enforcement; residual reflection paths are
        lint/CI-covered).
        """
        _verify(token)
        self._records[(record_class, key)] = record

    def items(self, record_class: str) -> tuple[tuple[str, object], ...]:
        """Every ``(key, record)`` pair in one class, key-sorted."""
        return tuple(
            (key, record)
            for (cls, key), record in sorted(self._records.items())
            if cls == record_class
        )


class AuditedStateWriter:
    """The ergonomic — and only supported — Control Plane state-write surface.

    Constructor-injected (store + the one existing
    :class:`~ccf.controlplane.audit.AuditLog`, keyword-only, house pattern),
    it mints the :class:`StateWriteToken` internally, performs the write, and
    appends the caller's domain event — both mechanisms of D-08 in one place:
    the audit-bearing path as the ergonomic surface, the token as what the
    raw seam requires.

    **Audit-event policy (fixed in 07-02; INV-CH7-71).** ``write`` takes the
    caller's domain :class:`~ccf.controlplane.audit.AuditEvent` as a required
    parameter and appends exactly that one event per write: the write
    evidence rides on the domain event, so domain transition evidence is
    never lost and the journal never doubled. The log reassigns the
    ``sequence`` on append — sequencing belongs to the log, which is its own
    stated contract ("callers cannot mis-number the log"); every other field
    is the caller's, verbatim. Callers with no domain semantics use the
    generic ``state_written`` :data:`~ccf.controlplane.audit.AuditAction`.

    There is no parallel log type: this appends to
    :class:`~ccf.controlplane.audit.AuditLog` and nothing else (D-08).
    """

    def __init__(
        self, *, store: ControlPlaneStateStore, audit: AuditLog
    ) -> None:
        self._store = store
        self._audit = audit

    def write(
        self,
        record_class: str,
        key: str,
        record: object,
        *,
        event: AuditEvent,
    ) -> AuditEvent:
        """Write ``record`` and append ``event`` — one write, one event.

        Returns the appended event, sequence assigned by the log.
        """
        self._store.put(
            record_class, key, record, token=StateWriteToken(_STATE_WRITE_TOKEN)
        )
        return self._audit.append(
            action=event.action,
            key=event.key,
            version=event.version,
            resolved=event.resolved,
            occurred_at=event.occurred_at,
            actor=event.actor,
            artifact_class=event.artifact_class,
        )
