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
    EntityRecord,
    GraphQuery,
    GraphReader,
    GraphView,
    RelationshipRecord,
    SourceAttestation,
)
from ccf.projection.engine import ExecutionResult
from ccf.replay.record import ContextFabricSnapshot

__ccf_mode__ = "algorithmic"

__all__ = [
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


class SnapshotReader:
    """A :class:`~ccf.graph.protocols.GraphReader` pinned to one logical snapshot.

    Delegates to the live reader — there is no copy — but admits only the
    ``(tenant_id, temporal_boundary)`` pair the snapshot names. Because the
    graph is append-only with logical supersession (INV-CH7-04) and reads are
    bitemporal (INV-CH7-14), that delegated read returns the state of the
    decision's instant however much has been written since.

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

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        """Re-render the recorded state; refuse anything else.

        Raises:
            SnapshotScopeViolation: ``tenant_id`` or ``at`` is outside the
                snapshot.
        """
        self._check(tenant_id=tenant_id, at=at)
        return self._reader.as_of(tenant_id=tenant_id, at=at)

    def query(self, q: GraphQuery) -> GraphView:
        """Answer ``q`` within the pinned snapshot scope; refuse anything else.

        The scope check runs over the query's own fields — ``q.tenant_id``
        must equal the pinned tenant and ``q.as_of`` the pinned temporal
        boundary — before any delegation, so a replayed execution cannot
        read outside the snapshot however its queries are phrased. The
        raise-on-mismatch here versus the empty view a source answers is
        deliberate and both behaviors are normative (`GQ-27` at
        docs/GRAPH_QUERY_SEMANTICS.md:529 — see :meth:`_check`).

        Raises:
            SnapshotScopeViolation: ``q.tenant_id`` or ``q.as_of`` is
                outside the snapshot.
        """
        self._check(tenant_id=q.tenant_id, at=q.as_of)
        return self._reader.query(q)

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
    )
