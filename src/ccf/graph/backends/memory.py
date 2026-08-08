"""In-memory ``GraphStore`` — the zero-dependency KV floor of the read seam.

Whitepaper §7.3 (the Context Graph as first-class persisted state); the
Phase 15.2 D-06 ruling
(``.planning/phases/15.2-substrate-adapters-and-query-pushdown/15.2-CONTEXT.md``):
the memory backend is deliberately the **teaching example of an adapter with no
query engine**. A dict store, a typed write transaction over dicts (in
``ccf.graph._writer``, where every write path lives — CINV-02), and a reader
that feeds dict rows into the substrate-neutral materialization core and lets
``ccf.graph.fallback`` answer. Zero third-party imports: proof that the
``GraphReader`` seam requires no query engine at all, and the shape every
future adapter's degrade path already has (`GQ-29` at
docs/GRAPH_QUERY_SEMANTICS.md:554, D-04).

**What this module deliberately does not contain.**

* **Any way to write.** Exactly as the SQLite backend: the store owns the
  state; every mutation lives in ``ccf.graph._writer`` behind the CINV-02
  lint (``_MemoryTxn`` / ``MemoryGraphWriter``).
* **Any materialization, ordering, freezing, or traversal of its own.**
  Record construction with the lineage-at-boundary and supersession-as-of
  rules lives only in :mod:`ccf.graph.reader`'s core; answering lives only in
  :mod:`ccf.graph.fallback`; ordering lives only in the interface (`GQ-22` at
  docs/GRAPH_QUERY_SEMANTICS.md:461). The one "as of" thing this module
  expresses natively is the **row filter** — the same predicate the SQL
  backends express in their ``SELECT_*_AS_OF`` statements — which
  :func:`ccf.graph.reader.materialize_view` documents as the caller's job.
  Everything above the rows is shared, so the semantics cannot fork here
  (15.2-RESEARCH.md Pitfall 5).

**Physical layout.** Five per-tenant dicts mirroring the five relational
tables field-for-field, so a claim dict satisfies the
:class:`ccf.graph.reader.Row` Protocol and feeds the shared materialization
core unchanged. Timestamps are stored as canonical RFC3339 UTC text
(:func:`ccf.contracts.canonical.canonical_timestamp`), never ``datetime``
objects — lexicographic comparison of canonical text is chronological, and one
rendering is what keeps the conformance suite's canonical-bytes comparisons
byte-identical across substrates rather than merely similar
(04-RESEARCH.md Pitfall 3).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from types import TracebackType
from typing import TypedDict

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph import fallback
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    RelationshipRecord,
    SourceAttestation,
)
from ccf.graph.reader import (
    Row,
    _entity_records,
    _LineageRowsFor,
    _ordered_view,
    _relationship_records,
    materialize_view,
)

__ccf_mode__ = "algorithmic"

__all__ = ["MemoryGraphReader", "MemoryGraphStore"]


class EntityNodeRow(TypedDict):
    """One row of the ``entities`` table, as a dict. Timestamps are canonical text."""

    entity_class: str
    first_observed_at: str
    last_observed_at: str


class RelationshipNodeRow(TypedDict):
    """One row of the ``relationships`` table, as a dict. Timestamps are canonical text."""

    relationship_type: str
    subject_uri: str
    object_uri: str
    first_observed_at: str
    last_observed_at: str


class EntityClaimRow(TypedDict):
    """One row of the ``entity_claims`` table, as a dict.

    Field names mirror the SQL columns exactly, so this dict satisfies the
    :class:`ccf.graph.reader.Row` Protocol and feeds the shared
    materialization core unchanged. ``observed_at`` and ``superseded_at`` are
    canonical RFC3339 text (``str``), never ``datetime`` — the cross-backend
    byte-drift trap the module docstring names.
    """

    entity_uri: str
    claim_id: str
    claim_json: str
    observed_at: str
    policy_bundle_version: str
    superseded_by: str | None
    superseded_at: str | None


class RelationshipClaimRow(TypedDict):
    """One row of the ``relationship_claims`` table, as a dict.

    As :class:`EntityClaimRow`, keyed on ``relationship_key``.
    """

    relationship_key: str
    claim_id: str
    claim_json: str
    observed_at: str
    policy_bundle_version: str
    superseded_by: str | None
    superseded_at: str | None


class LineageRow(TypedDict):
    """One row of the ``lineage`` table, as a dict."""

    entry_json: str


@dataclass
class TenantState:
    """One tenant's five in-memory tables, mirroring the relational shape.

    Graph-tier internal (deliberately outside ``__all__``): its only readers
    are :class:`MemoryGraphReader` and the writer machinery in
    ``ccf.graph._writer``. Per-tenant partitioning is structural — a read for
    one tenant is handed this object and cannot see another tenant's dicts,
    which is the memory rendering of the compound-uniqueness tenancy
    discipline (INV-CH7-16, D-IMPL-05).

    Dict insertion order is arrival order, which is the memory backend's
    ``rowid``: the writer's chain reads sort by ``observed_at`` with a stable
    sort, so ties break by arrival exactly as the SQL backends'
    ``ORDER BY observed_at, rowid``.
    """

    #: ``entity_uri`` -> node identity row.
    entity_nodes: dict[str, EntityNodeRow] = field(default_factory=dict)
    #: ``entity_uri`` -> ``claim_id`` -> claim row (append-only; the only
    #: fields ever mutated after insert are the supersession pair —
    #: INV-CH7-04).
    entity_claims: dict[str, dict[str, EntityClaimRow]] = field(
        default_factory=dict
    )
    #: ``relationship_key`` -> node identity row.
    relationship_nodes: dict[str, RelationshipNodeRow] = field(
        default_factory=dict
    )
    #: ``relationship_key`` -> ``claim_id`` -> claim row.
    relationship_claims: dict[str, dict[str, RelationshipClaimRow]] = field(
        default_factory=dict
    )
    #: ``(claim_kind, node_key, claim_id)`` -> ``lineage_id`` -> entry row.
    #: Keying on the full entry identity is the L-axis set-union
    #: (INV-CH7-17): a re-delivered envelope collides and is ignored, a
    #: second source does not.
    lineage: dict[tuple[str, str, str], dict[str, LineageRow]] = field(
        default_factory=dict
    )


def _current_at(
    *, observed_at: str, superseded_at: str | None, boundary: str
) -> bool:
    """The as-of **row filter**, over canonical text.

    The one "as of" place a substrate expresses natively — the dict rendering
    of the SQL backends' ``observed_at <= ? AND (superseded_at IS NULL OR
    superseded_at > ?)`` predicate, compared lexicographically because
    canonical RFC3339 text sorts chronologically. This is deliberately NOT the
    supersession-as-of *edge* rule or the lineage-at-boundary rule: those are
    rendered only inside :func:`ccf.graph.reader.materialize_view`, which
    documents row filtering as the caller's job and everything above the rows
    as its own (15.2-RESEARCH.md Pitfall 5).
    """
    if observed_at > boundary:
        return False
    return superseded_at is None or superseded_at > boundary


class MemoryGraphStore:
    """State and identity owner for the in-memory backend — the D-06 KV floor.

    Whitepaper §7.3; the Phase 15.2 D-06 ruling. Zero external dependencies
    and zero persistence: the graph lives exactly as long as the instance,
    which is the point — always-on conformance legs and quickstart-grade
    fabrics need no substrate at all.

    The store is *not* a ``GraphStore`` in the sense of offering both halves
    of the Protocol: it offers :attr:`reader` and, to the writer module alone,
    the tenant state. Every mutation lives in ``ccf.graph._writer`` behind
    the CINV-02 lint — exactly the SQLite arrangement.
    """

    def __init__(self) -> None:
        self._graph_identity = f"memory://{uuid.uuid4().hex}"
        self._tenants: dict[str, TenantState] = {}
        self._reader = MemoryGraphReader(self)

    @property
    def graph_identity(self) -> str:
        """Stable synthetic identity of this in-memory graph, minted at construction.

        The single-writer boot check keys on this via
        ``mint_boot_token(graph_identity=...)``: two writers over one store
        *instance* are the violation; two instances are two fabrics. The
        per-instance UUID already makes the identity globally unique, exactly
        as SQLite keys on its database path and Postgres on
        host/port/database.

        ``tenant_id`` is deliberately NOT part of the identity: the writer is
        per-store, never per-tenant (INV-CH7-10 — one writer per *graph*),
        and a tenant-suffixed identity would let two writers over the same
        store coexist by naming different tenants, which is precisely the
        interleaving the boot check exists to refuse.
        """
        return self._graph_identity

    def tenant_state(self, tenant_id: str) -> TenantState:
        """One tenant's tables, created empty on first touch.

        Reachable in principle by any importer, which is why every mutation —
        not merely the handle — lives in ``ccf.graph._writer`` behind the
        CINV-02 lint. The honest claim is DESIGN.md §9's: no unforced path
        exists, and every forced path fails CI or fails at boot.
        """
        state = self._tenants.get(tenant_id)
        if state is None:
            state = TenantState()
            self._tenants[tenant_id] = state
        return state

    @property
    def reader(self) -> MemoryGraphReader:
        """The read-only view of this graph — safe to hand to anyone."""
        return self._reader

    def close(self) -> None:
        """Release the graph state. An in-memory graph does not outlive its store."""
        self._tenants.clear()

    def __enter__(self) -> MemoryGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class MemoryGraphReader:
    """``GraphReader`` over the memory store's dicts — no query engine, by design.

    Structurally conforms to :class:`ccf.graph.protocols.GraphReader`. This
    class holds **no native translation and no answering logic**: it acquires
    the as-of rows from the dicts (the row filter, in Python), materializes
    them through the substrate-neutral core
    (:func:`ccf.graph.reader.materialize_view` — the only place record bytes
    are produced), applies :func:`ccf.graph.fallback.answer` for the query's
    predicate families and ``allowed_entities`` (handled there by
    set-intersection — no memory-specific code exists for it), and freezes
    through the interface-owned ordering (`GQ-22` at
    docs/GRAPH_QUERY_SEMANTICS.md:461). That is the whole class — the
    teaching example of the D-06 ruling: **an adapter needs no query engine**,
    because the fallback is the one scan-and-filter every adapter degrades to
    (`GQ-29` at docs/GRAPH_QUERY_SEMANTICS.md:554, D-04).
    """

    def __init__(self, store: MemoryGraphStore) -> None:
        self._store = store

    def _lineage_rows_for(self, tenant_id: str) -> _LineageRowsFor:
        """A lineage supplier over the tenant's lineage dict.

        Returns *rows*, not lineage: the boundary rendering happens inside
        the materialization core and cannot be reimplemented here — exactly
        the SQL client's arrangement, with an index lookup where the SQL
        client closes over its ``SELECT_LINEAGE`` statement.
        """
        state = self._store.tenant_state(tenant_id)

        def rows_for(kind: str, node_key: str, claim_id: str) -> tuple[Row, ...]:
            return tuple(state.lineage.get((kind, node_key, claim_id), {}).values())

        return rows_for

    def query(self, q: GraphQuery) -> GraphView:
        """Answer ``q`` — always through the shared degrade path.

        There is no substrate translation here and never will be one worth
        writing: a dict store holds no query engine, so every answer flows
        through :func:`ccf.graph.fallback.answer` over rows materialized by
        the shared core. An empty answer is an answer, never an error
        (`GQ-23` at docs/GRAPH_QUERY_SEMANTICS.md:474). Tenant scope arrives
        inside the frozen value; ``q.as_of`` arrives as data — this method
        reads no clock.
        """
        boundary = canonical_timestamp(q.as_of)
        state = self._store.tenant_state(q.tenant_id)
        entity_rows: tuple[Row, ...] = tuple(
            row
            for claims in state.entity_claims.values()
            for row in claims.values()
            if _current_at(
                observed_at=row["observed_at"],
                superseded_at=row["superseded_at"],
                boundary=boundary,
            )
        )
        relationship_rows: tuple[Row, ...] = tuple(
            row
            for claims in state.relationship_claims.values()
            for row in claims.values()
            if _current_at(
                observed_at=row["observed_at"],
                superseded_at=row["superseded_at"],
                boundary=boundary,
            )
        )
        materialized = materialize_view(
            entity_rows=entity_rows,
            relationship_rows=relationship_rows,
            tenant_id=q.tenant_id,
            as_of=q.as_of,
            lineage_rows_for=self._lineage_rows_for(q.tenant_id),
        )
        entities, relationships = fallback.answer(
            materialized.entities, materialized.relationships, query=q
        )
        return _ordered_view(
            tenant_id=q.tenant_id,
            as_of=q.as_of,
            entities=entities,
            relationships=relationships,
        )

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        """Return the state ``tenant_id``'s graph held at observed-time ``at``.

        The D-07 derivation, exactly as ``BaseGraphReader``'s: ``as_of`` is
        **defined** as the degenerate everything-question — `GQ-21` at
        docs/GRAPH_QUERY_SEMANTICS.md:446.
        """
        return self.query(GraphQuery(tenant_id=tenant_id, as_of=at))

    @property
    def attestation(self) -> SourceAttestation:
        """Tier 1 — the live graph's well-known attestation value (D-09).

        SDK-defined per CLAUDE.md §11: an in-memory graph is still the live
        graph — policy bindings were stamped by the fabric's own L2 at
        assembly time and lineage is the graph's own accumulated L, with no
        federation peer involved. Persistence is not an attestation
        dimension.
        """
        return SourceAttestation(
            policy_binding="assembly-stamped",
            lineage="graph-supplied",
            peer=None,
        )

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        """Return every claim ever made about ``entity_uri``, oldest first."""
        state = self._store.tenant_state(tenant_id)
        rows = tuple(
            sorted(
                state.entity_claims.get(entity_uri, {}).values(),
                key=lambda row: row["observed_at"],
            )
        )
        return _entity_records(
            rows, lineage_rows_for=self._lineage_rows_for(tenant_id)
        )

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        """Return every claim ever made about one edge, oldest first."""
        state = self._store.tenant_state(tenant_id)
        rows = tuple(
            sorted(
                state.relationship_claims.get(relationship_key, {}).values(),
                key=lambda row: row["observed_at"],
            )
        )
        return _relationship_records(
            rows, lineage_rows_for=self._lineage_rows_for(tenant_id)
        )
