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
suspended workflow execution state. What does not: the artifacts themselves.
A grant *artifact* is immutable and registers append-only into the versioned
registry; only the grant's *state* lives here. Confusing the two is the
mutability rule failing (D-IMPL-27).

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

**Writes carry two proofs, and they are different facts.**

* **Audited by construction — D-22-scoped (07-02; D-20 closure).** ``put``
  requires a :class:`StateWriteToken` that only this module mints, and the
  only supported minting path is :class:`AuditedStateWriter`, which appends
  the caller's domain :class:`~ccf.controlplane.audit.AuditEvent` to the one
  existing :class:`~ccf.controlplane.audit.AuditLog` on every write
  (INV-CH7-71: one audit plane, one event per write). An unaudited state
  write is therefore unrepresentable **through the public write surface**.
* **Authorized by construction — D-IMPL-353 §1.2, the derived-writes rule.**
  ``put`` also requires an :class:`~ccf.authz.capability.Authorized` of one
  of :data:`STATE_WRITE_KINDS` — the capability that authorized the action
  this write is a *consequence* of: the ``Execute`` / ``Resume`` that started
  or resumed the run whose state this is, the ``SkillGrant`` / ``SkillRevoke``
  whose transition this records. The store takes the **tenant** from that
  capability and from nothing else (§1.3): the key is derived by
  :func:`state_key` from ``authorized.tenant`` and the record's own identity
  within the tenant (``record_id`` — an execution id, a grant hash — which
  the writing mechanism generated *after* the decision and which the decision
  therefore could not name). A caller cannot supply the tenant, so a write
  under another tenant is not refused; it is inexpressible.

  The capability is verified before the dict is touched, by
  :func:`~ccf.authz.capability.verify` — mint, retargeting and kind by
  identity (§1.5c, g). Its resource axis is bound to the capability's own
  resource: for a derived write the target did not exist when the decision
  was made, so there is nothing else to bind it to, and the design records
  that *"a mismatch is unreachable on the served path"* (§1.2). The tenant is
  where the authority bites, and it bites structurally.

Bypass via reflection or private construction (reaching for this module's
private sentinel, skipping ``__init__`` machinery) is not denied; it is out
of the claim's scope by design and is lint- and CI-covered instead (D-08,
D-22; D-IMPL-353 §5 — the same limit single-writer has).

**Reads remain unaudited and uncapabilitied, by scope of the same rulings.**
``get`` and ``items`` carry no token and append nothing: the closure governs
*writes*. A reader can enumerate state through ``items``; what it cannot do
is change state without leaving a record, or under a tenant it was not
authorized for.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Final, Protocol, TypeAlias, runtime_checkable

from ccf.authz.capability import (
    verify_any,
    ActionKind,
    Authorized,
    Execute,
    Resume,
    SkillGrant,
    SkillRevoke,
    verify,
)
from ccf.controlplane.audit import AuditEvent, AuditLog

__ccf_mode__ = "algorithmic"

__all__ = [
    "STATE_KEY_SEPARATOR",
    "STATE_WRITE_KINDS",
    "AuditedStateWriter",
    "ControlPlaneStateStore",
    "InMemoryStateStore",
    "StateKeyError",
    "StateTenantMismatch",
    "StateWriteAuthority",
    "StateWriteBypassError",
    "StateWriteToken",
    "split_state_key",
    "state_key",
    "verify_any",
]


class StateWriteBypassError(TypeError):
    """A state write was attempted outside the audited write path.

    The same discipline as
    :class:`~ccf.peering.admission.AdmissionBypassError`: the token type is
    constructible only inside this module, so holding one *is* the evidence
    the audited path ran (D-08; D-22-scoped — public write surface only).
    """


class StateKeyError(ValueError):
    """A state key could not be derived unambiguously (D-IMPL-353 §1.3).

    The key is ``{tenant}{sep}{record_id}`` and must split back to exactly
    the pair that built it, or two tenants could share a key. A tenant that
    is empty, untrimmed, or carries the separator is refused at derivation —
    a misconfiguration surfaced where the operator sees it, never a decision
    about any caller.
    """


class StateTenantMismatch(PermissionError):
    """A record claims a tenant other than the capability's (D-IMPL-353 §1.3).

    Records are opaque to the store, with one exception the design requires:
    a record that *declares* a ``tenant`` must declare the capability's. The
    store files under ``authorized.tenant`` and nothing else may name one, so
    a record carrying another tenant would be filed under a tenant it does not
    describe — broken wiring, refused before the dict is touched.
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


# --- the capability half (D-IMPL-353) ---------------------------------------

#: The kinds whose handles write Control Plane state as a consequence of the
#: action they perform (§1.2, the derived-writes rule): the workflow engine
#: under the ``Execute`` / ``Resume`` that authorized the run, the grant
#: ledger under the ``SkillGrant`` / ``SkillRevoke`` whose transition it
#: records. A tuple, not a set: the order is the order a diagnostic names
#: them in. SDK action kinds are mechanism, not domain values (CINV-01).
STATE_WRITE_KINDS: Final[tuple[type[ActionKind], ...]] = (
    Execute,
    Resume,
    SkillGrant,
    SkillRevoke,
)

#: The static type of ``put``'s first parameter — the union of the four, so a
#: handler holding any other kind is a ``mypy --strict`` error at the call.
StateWriteAuthority: TypeAlias = (
    Authorized[Execute]
    | Authorized[Resume]
    | Authorized[SkillGrant]
    | Authorized[SkillRevoke]
)


#: The one character between the tenant and the record id in a state key.
#: The engine keyed ``{tenant}/{execution_id}`` before the derivation moved
#: here; keeping the character keeps every recorded key readable.
STATE_KEY_SEPARATOR: Final[str] = "/"


def state_key(*, tenant: str, record_id: str) -> str:
    """The key a state record lives under: ``{tenant}/{record_id}`` (§1.3).

    Derived, never spelled by a caller. Injective: the tenant may not carry
    the separator (nor be empty or untrimmed), so splitting at the *first*
    separator recovers exactly the pair — a record id is free to contain it.

    Raises:
        StateKeyError: the tenant or record id cannot make an unambiguous key.
    """
    if not tenant or tenant != tenant.strip() or STATE_KEY_SEPARATOR in tenant:
        raise StateKeyError(
            f"tenant {tenant!r} cannot form a state key: a tenant must be a"
            f" non-empty, trimmed string without {STATE_KEY_SEPARATOR!r}, or"
            " two tenants could share one key (D-IMPL-353 §1.3)"
        )
    if not record_id:
        raise StateKeyError(
            "a state record needs an identity within its tenant; an empty"
            " record id names nothing (D-IMPL-353 §1.2)"
        )
    return f"{tenant}{STATE_KEY_SEPARATOR}{record_id}"


def split_state_key(key: str) -> tuple[str, str]:
    """The ``(tenant, record_id)`` a :func:`state_key` was built from.

    Raises:
        StateKeyError: ``key`` carries no tenant segment.
    """
    tenant, separator, record_id = key.partition(STATE_KEY_SEPARATOR)
    if not separator or not tenant or not record_id:
        raise StateKeyError(
            f"{key!r} is not a state key: expected"
            f" '{{tenant}}{STATE_KEY_SEPARATOR}{{record_id}}' (D-IMPL-353 §1.3)"
        )
    return tenant, record_id


@runtime_checkable
class ControlPlaneStateStore(Protocol):
    """The mutable-state surface a Control Plane must offer (D-IMPL-18/27).

    Records are addressed by ``(record_class, key)``. ``record_class``
    partitions the namespace so unrelated machines never collide on a shared
    key; it is an opaque identifier owned by the consuming module, exactly as
    :class:`~ccf.controlplane.artifacts.ArtifactClass` is for artifacts. The
    key is :func:`state_key` of the writing capability's tenant and the
    record's own id; readers derive the same key the same way.

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
        authorized: StateWriteAuthority,
        record_class: str,
        record: object,
        *,
        record_id: str,
        token: StateWriteToken,
    ) -> None:
        """Write ``record`` under ``state_key(authorized.tenant, record_id)``, replacing any prior record.

        ``authorized`` is the D-IMPL-353 proof: the capability for the action
        this write is a consequence of (:data:`STATE_WRITE_KINDS`), verified
        before anything is touched, and the only source of the tenant.
        ``token`` is the D-20 closure: only the audited write path
        (:class:`AuditedStateWriter`) mints one. An implementation that
        honours this signature cannot be written to unaudited, nor under a
        tenant nobody authorized, through the public write surface.
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
        authorized: StateWriteAuthority,
        record_class: str,
        record: object,
        *,
        record_id: str,
        token: StateWriteToken,
    ) -> None:
        """Write ``record`` under the derived key, replacing any prior record.

        Order is the order of proofs: the capability first (D-IMPL-353
        §1.5 — fabricated, retargeted or wrong-kind dies here, before the
        token is even read), then the token's mint (D-22), then the key is
        derived from the capability's tenant and the dict is touched. A
        refusal at either proof leaves the store byte-for-byte as it was.
        """
        verify_any(
            authorized,
            kinds=STATE_WRITE_KINDS,
            resource=getattr(authorized, "resource", ""),
        )
        _verify(token)
        claimed = getattr(record, "tenant", authorized.tenant)
        if claimed != authorized.tenant:
            raise StateTenantMismatch(
                f"the record declares tenant {claimed!r} but the capability is"
                f" for {authorized.tenant!r}; state is filed under the"
                " capability's tenant and a record may not name another"
                " (D-IMPL-353 §1.3)"
            )
        key = state_key(tenant=authorized.tenant, record_id=record_id)
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
    raw seam requires. The capability is *not* minted here: it arrives from
    the handle that holds it, and travels through unchanged (D-IMPL-353 §1.2).

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
        authorized: StateWriteAuthority,
        record_class: str,
        record: object,
        *,
        record_id: str,
        event: AuditEvent,
    ) -> AuditEvent:
        """Write ``record`` and append ``event`` — one write, one event.

        The store verifies ``authorized``; a refusal there propagates and no
        event is appended, because there was no write to evidence.

        Returns the appended event, sequence assigned by the log.
        """
        self._store.put(
            authorized,
            record_class,
            record,
            record_id=record_id,
            token=StateWriteToken(_STATE_WRITE_TOKEN),
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

