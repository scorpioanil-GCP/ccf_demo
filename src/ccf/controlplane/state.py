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

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__ccf_mode__ = "algorithmic"

__all__ = ["ControlPlaneStateStore", "InMemoryStateStore"]


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

    def put(self, record_class: str, key: str, record: object) -> None:
        """Write ``record`` under ``key``, replacing any prior record."""
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

    def put(self, record_class: str, key: str, record: object) -> None:
        """Write ``record`` under ``key``, replacing any prior record."""
        self._records[(record_class, key)] = record

    def items(self, record_class: str) -> tuple[tuple[str, object], ...]:
        """Every ``(key, record)`` pair in one class, key-sorted."""
        return tuple(
            (key, record)
            for (cls, key), record in sorted(self._records.items())
            if cls == record_class
        )
