"""Logical snapshot resolution — replay's view of the graph (D-IMPL-06).

Whitepaper §7.10.1 dimension 1 (the touched ``G(E, R, T, P, Π, L)`` substate at
decision time, INV-CH7-81); DESIGN.md §2B.5.

**Why the snapshot is logical.** A physical graph copy per decision is what
makes year-scale replay intractable: a fabric serving a thousand products a day
would be storing a thousand graph copies a day, and the copies would dwarf the
graph. The whitepaper does not require a copy — it requires the *state at
decision time*, and an append-only bitemporal graph already holds every state
it has ever held. So a snapshot is four facts:

* the tenant the read was scoped to,
* the temporal boundary it was taken as of,
* a watermark identifying the state actually read, and
* the manifest of entities and relationships the decision touched.

Feeding the boundary back to an as-of read re-renders the state, and the
watermark plus the manifest are how a replay *checks* that it did.

**The reader is a scope, not a suggestion.** :class:`SnapshotReader` pins the
tenant and the boundary and refuses every other read. A replay that could read
at any instant it liked would be re-computation wearing a snapshot's name — and
the failure mode is the worst kind, because it would silently import the future
into a record of the past.

Read-only throughout: this module names no writer and constructs none. The
single-writer invariant (CLAUDE.md §10) is not something replay could weaken
even if it tried, because there is no write handle in any signature here.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from ccf.graph.protocols import (
    NO_STORE_SNAPSHOT_PIN,
    EntityRecord,
    GraphQuery,
    GraphReader,
    GraphView,
    RelationshipRecord,
    SnapshotPinnable,
    SourceAttestation,
    StoreSnapshotPin,
)
from ccf.projection.engine import ExecutionResult
from ccf.replay.record import ContextFabricSnapshot

__ccf_mode__ = "algorithmic"

__all__ = [
    "SnapshotPinUnresolvable",
    "SnapshotReader",
    "SnapshotScopeViolation",
    "snapshot_of_execution",
]


class SnapshotScopeViolation(LookupError):
    """A read was attempted outside the snapshot the replay is pinned to.

    Raised rather than quietly answered: a replay reading a tenant or an
    instant the record does not name is not replaying that record, and
    returning state for it would produce a confident answer to a question
    nobody asked.
    """


class SnapshotPinUnresolvable(LookupError):
    """A record pins the store at a transaction the live reader cannot resolve.

    SDK-defined per CLAUDE.md §11, beside the whitepaper's replay commitment
    (§7.10) and the exact-version rule of CLAUDE.md §7.4 (ledger row
    24.5-L-02, D-IMPL-240). Raised when dimension 1 carries a
    :class:`~ccf.graph.protocols.StoreSnapshotPin` other than the sentinel
    and the reader handed to replay is not
    :class:`~ccf.graph.protocols.SnapshotPinnable` — a reader that can only
    answer the head. Replay **refuses** rather than reading the head: the
    head is the store's state *now*, and a decision replayed against it
    would be a new decision wearing the recorded one's identifier. A
    ``LookupError`` because it is the same class of failure as
    :class:`~ccf.replay.engine.ReplayUnresolvable` — something the record
    names cannot be resolved as recorded — and the engine reports it that
    way.
    """


class SnapshotReader:
    """A :class:`~ccf.graph.protocols.GraphReader` pinned to one logical snapshot.

    Delegates to the live reader — there is no copy — but admits only the
    ``(tenant_id, temporal_boundary)`` pair the snapshot names. Because the
    graph is append-only with logical supersession (INV-CH7-04) and reads are
    bitemporal (INV-CH7-14), that delegated read returns the state of the
    decision's instant however much has been written since.

    **The recorded store pin is resolved exactly, and the head is never a
    fallback** (ledger row 24.5-L-02; D-IMPL-240 (1); CLAUDE.md §7.4 replay
    determinism). When the snapshot carries a
    :class:`~ccf.graph.protocols.StoreSnapshotPin` other than
    :data:`~ccf.graph.protocols.NO_STORE_SNAPSHOT_PIN`, every read —
    :meth:`as_of`, which is the degenerate query (`GQ-21`), and
    :meth:`query` alike — is answered through the live reader's
    ``query_pinned`` at that pin, so a substrate whose head has advanced
    since the decision still re-renders the state the decision read. A
    live reader that is not :class:`~ccf.graph.protocols.SnapshotPinnable`
    cannot honor such a pin, and the reader raises
    :class:`SnapshotPinUnresolvable` rather than answering the head: an
    answer from the current head would be a confident re-computation
    wearing the record's identifier. When the sentinel is recorded, the
    reads behave exactly as they did before the pin existed — the
    compatibility promise every pre-phase record relies on.

    The reader is itself :class:`~ccf.graph.protocols.SnapshotPinnable`:
    :meth:`snapshot_pin` reports the *recorded* pin, so an execution driven
    through it carries the recorded pin on its result and
    :func:`snapshot_of_execution` re-derives dimension 1 with the pin the
    record names, and :meth:`query_pinned` admits only that pin.

    Args:
        reader: The live graph reader. Read-only by type; the replay path has
            no way to obtain a writer.
        snapshot: The recorded dimension-1 snapshot to pin to.
    """

    def __init__(
        self, *, reader: GraphReader, snapshot: ContextFabricSnapshot
    ) -> None:
        self._reader = reader
        self._snapshot = snapshot

    @property
    def snapshot(self) -> ContextFabricSnapshot:
        """The snapshot this reader is pinned to."""
        return self._snapshot

    def _check(self, *, tenant_id: str, at: datetime | None = None) -> None:
        """Refuse any scope outside the pinned ``(tenant, boundary)`` pair.

        Raising here — rather than answering the empty view a *source*
        answers on a tenant mismatch — is the deliberate contrast the
        tenant-mismatch clause states (`GQ-27` at
        docs/GRAPH_QUERY_SEMANTICS.md:529): a source answers questions; a
        pin enforces one. A replay reading outside its pin is a broken
        replay, and a quiet answer would be a confident answer to a
        question nobody asked.
        """
        if tenant_id != self._snapshot.tenant_id:
            raise SnapshotScopeViolation(
                f"replay is pinned to tenant {self._snapshot.tenant_id!r}; "
                f"{tenant_id!r} is outside the recorded snapshot"
            )
        if at is not None and at != self._snapshot.temporal_boundary:
            raise SnapshotScopeViolation(
                f"replay is pinned to the recorded temporal boundary "
                f"{self._snapshot.temporal_boundary.isoformat()}; a read as of "
                f"{at.isoformat()} would be a different decision"
            )

    def _pinned_reader(self) -> SnapshotPinnable:
        """The live reader, proven able to honor the recorded pin — or refuse.

        Raises:
            SnapshotPinUnresolvable: the snapshot records a store pin and the
                live reader is not :class:`~ccf.graph.protocols.SnapshotPinnable`.
                Never answers the head instead (CLAUDE.md §7.4).
        """
        if isinstance(self._reader, SnapshotPinnable):
            return self._reader
        pin = self._snapshot.store_snapshot_pin
        raise SnapshotPinUnresolvable(
            f"the record pins the store at {pin.substrate}:{pin.pin!r} and the "
            f"live reader ({type(self._reader).__name__}) cannot resolve a "
            "store pin; replay refuses to read the current head in its place "
            "(24.5-L-02, CLAUDE.md §7.4)"
        )

    def _routed(self, q: GraphQuery) -> GraphView:
        """Answer ``q`` at the recorded pin when one is recorded; as before otherwise."""
        pin = self._snapshot.store_snapshot_pin
        if pin == NO_STORE_SNAPSHOT_PIN:
            return self._reader.query(q)
        return self._pinned_reader().query_pinned(q, pin=pin)

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        """Re-render the recorded state; refuse anything else.

        With a store pin recorded, this is the degenerate query (`GQ-21`)
        answered at that pin; with the sentinel recorded, the live reader's
        own ``as_of`` exactly as before.

        Raises:
            SnapshotScopeViolation: ``tenant_id`` or ``at`` is outside the
                snapshot.
            SnapshotPinUnresolvable: a store pin is recorded and the live
                reader cannot resolve one.
        """
        self._check(tenant_id=tenant_id, at=at)
        if self._snapshot.store_snapshot_pin == NO_STORE_SNAPSHOT_PIN:
            return self._reader.as_of(tenant_id=tenant_id, at=at)
        return self._routed(GraphQuery(tenant_id=tenant_id, as_of=at))

    def query(self, q: GraphQuery) -> GraphView:
        """Answer ``q`` within the pinned snapshot scope; refuse anything else.

        The scope check runs over the query's own fields — ``q.tenant_id``
        must equal the pinned tenant and ``q.as_of`` the pinned temporal
        boundary — before any delegation, so a replayed execution cannot
        read outside the snapshot however its queries are phrased. The
        raise-on-mismatch here versus the empty view a source answers is
        deliberate and both behaviors are normative (`GQ-27` at
        docs/GRAPH_QUERY_SEMANTICS.md:529 — see :meth:`_check`).

        With a store pin recorded the delegation is ``query_pinned`` at that
        pin (24.5-L-02); with the sentinel recorded it is ``query`` exactly
        as before.

        Raises:
            SnapshotScopeViolation: ``q.tenant_id`` or ``q.as_of`` is
                outside the snapshot.
            SnapshotPinUnresolvable: a store pin is recorded and the live
                reader cannot resolve one.
        """
        self._check(tenant_id=q.tenant_id, at=q.as_of)
        return self._routed(q)

    def snapshot_pin(self) -> StoreSnapshotPin:
        """The *recorded* pin — never the live reader's head.

        This is what makes the reader :class:`~ccf.graph.protocols.SnapshotPinnable`
        and what makes replay's re-derived dimension 1 carry the pin the
        record names: :meth:`ProjectionEngine.execute
        <ccf.projection.engine.ProjectionEngine.execute>` reads it once
        before its first query, exactly as it does on a live reader.
        """
        return self._snapshot.store_snapshot_pin

    def query_pinned(self, q: GraphQuery, *, pin: StoreSnapshotPin) -> GraphView:
        """Answer ``q`` at ``pin`` — admitted only when ``pin`` is the recorded one.

        Raises:
            SnapshotScopeViolation: ``pin`` is not the recorded pin (a
                replay asking for another state of the store is not
                replaying this record), or ``q`` is outside the snapshot.
            SnapshotPinUnresolvable: the live reader cannot resolve a pin.
        """
        recorded = self._snapshot.store_snapshot_pin
        if pin != recorded:
            raise SnapshotScopeViolation(
                f"replay is pinned to store state {recorded.substrate}:"
                f"{recorded.pin!r}; a read at {pin.substrate}:{pin.pin!r} "
                "would be a different decision"
            )
        self._check(tenant_id=q.tenant_id, at=q.as_of)
        return self._pinned_reader().query_pinned(q, pin=pin)

    @property
    def attestation(self) -> SourceAttestation:
        """The wrapped reader's attestation, unchanged.

        A snapshot pin narrows *scope*, not provenance: the records a
        pinned read answers acquired their policy binding and lineage
        exactly as the live reader's answers did, so the reported modes
        are the wrapped reader's own.
        """
        return self._reader.attestation

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        """Full claim history for one entity, within the snapshot's tenant.

        Not boundary-scoped: a *history* is by definition the whole record, and
        the caller asking for it has already said it wants more than the
        as-of view. The tenant scope still holds.
        """
        self._check(tenant_id=tenant_id)
        return self._reader.entity_history(tenant_id=tenant_id, entity_uri=entity_uri)

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        """Full claim history for one edge, within the snapshot's tenant."""
        self._check(tenant_id=tenant_id)
        return self._reader.relationship_history(
            tenant_id=tenant_id, relationship_key=relationship_key
        )


def snapshot_of_execution(
    *, execution: ExecutionResult, tenant_id: str, temporal_boundary: datetime
) -> ContextFabricSnapshot:
    """Derive the dimension-1 snapshot an execution result implies.

    The same derivation :func:`~ccf.replay.record.build_replay_record` performs
    at serve time, factored out so replay can perform it again over the
    *re-executed* result and compare the two ids. Two snapshots agreeing is
    then a statement about the state, because the id is content-derived rather
    than assigned.
    """
    return ContextFabricSnapshot.build(
        tenant_id=tenant_id,
        temporal_boundary=temporal_boundary,
        store_watermark=execution.state_watermark(),
        touched_entities=execution.touched_entities(),
        touched_relationships=execution.touched_relationships(),
        # 24.5-L-02: re-derived from the execution exactly as the id
        # constituents are, so replay compares the pin it read under with
        # the pin the record names.
        store_snapshot_pin=execution.store_snapshot_pin,
    )
