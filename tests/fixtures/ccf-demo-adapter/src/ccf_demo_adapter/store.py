"""State and the read seam for the demo adapter, over one in-process dict.

Plan 15.4-10, D-11. This module holds everything a reader needs and nothing a
writer needs; the write path lives in :mod:`ccf_demo_adapter.demo_write`, which
imports this module and is never imported by it.

**The backing store is two plain dictionaries with flat tuple keys, and that is
a design choice rather than laziness.** The SDK already ships an in-memory
adapter whose physical layout mirrors five relational tables field-for-field.
Copying it would prove the copy works, not that the seam works. So the layout
here is deliberately unlike it: one dict for node observation windows, one dict
for claims, both keyed by a whole tuple rather than nested per tenant, and each
claim carries its own lineage inside it instead of a separate lineage table.
Anything the SDK cannot express over *this* shape is a finding about the seam.

**Rows are objects, not dicts.** :class:`ccf.graph.reader.Row` is a Protocol
asking only for ``__getitem__``, so :class:`_Claim` satisfies it by mapping
column names onto its own attributes — including the two names the shared
materialization core uses for the node key on each axis. Both reference
adapters hand it dicts; handing it something else is worth doing once, because
it is the difference between a Protocol and a convention.

**This reader declines pushdown for every query, and that is the point.** A
dict store holds no query engine, so there is no predicate family it could
translate honestly. Declining is a first-class outcome — `GQ-29` at
docs/GRAPH_QUERY_SEMANTICS.md:554 — and the shared fallback then enforces the
whole query over materialized records. That is precisely the tier a third-party
adapter can reach without reimplementing the query surface, so it is the tier
this proof should exercise.

**One graph, one name.** :attr:`DemoGraphStore.graph_identity` is derived from
an explicit ``graph_name`` setting, exactly as the SQLite adapter derives its
identity from a database path. Two stores opened on one name are two handles on
one graph and share state; two stores on different names are two graphs. That
matters in both directions: an identity that collided across genuinely
different graphs would make the single-writer check refuse a boot for no
reason, and an identity that differed per instance would let two writers
coexist over one graph.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from types import TracebackType
from typing import Any

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
    ENTITY_KIND,
    RELATIONSHIP_KIND,
    Row,
    _entity_records,
    _LineageRowsFor,
    _ordered_view,
    _relationship_records,
    materialize_view,
)

__all__ = ["DemoGraphReader", "DemoGraphStore"]

#: Prefix of every graph identity this adapter mints. A scheme rather than a
#: bare name so an identity from this adapter cannot collide with one from
#: another adapter that happened to be handed the same setting.
IDENTITY_SCHEME = "demo://"

#: Column names the shared materialization core asks a row for that this
#: adapter does not store under that name. Both axes address one node key here,
#: because the store is one flat claim table discriminated by kind rather than
#: two tables named after their axis.
_NODE_KEY_COLUMNS = ("entity_uri", "relationship_key")


@dataclass
class _Node:
    """One node's identity row: what it is, and the window it was observed in.

    ``first_observed_at`` only ever moves earlier and ``last_observed_at`` only
    ever moves later, both as canonical RFC3339 text so that lexicographic
    comparison is chronological. ``subject_uri`` and ``object_uri`` are set for
    an edge and ``None`` for an entity — one row type for both axes, since the
    key already carries the discriminator.
    """

    node_class: str
    first_observed_at: str
    last_observed_at: str
    subject_uri: str | None = None
    object_uri: str | None = None


@dataclass
class _Claim:
    """One claim, and the lineage accumulated against it.

    Satisfies :class:`ccf.graph.reader.Row` through :meth:`__getitem__`, so it
    feeds the shared materialization core with no dict in between.

    Lineage lives here, keyed by the lineage id, rather than in a table of its
    own. Keying on the id *is* the L-axis set-union: a re-delivered envelope
    collides and is dropped, a second source does not.

    Nothing on this record is ever removed and only the supersession pair is
    ever reassigned after construction — that is what append-only-with-
    supersession means at the storage tier.
    """

    node_key: str
    claim_id: str
    claim_json: str
    observed_at: str
    policy_bundle_version: str
    superseded_by: str | None = None
    superseded_at: str | None = None
    lineage: dict[str, str] = field(default_factory=dict)

    def __getitem__(self, key: str, /) -> Any:
        """Address this claim by column name, for the shared read core.

        The core asks for the node key under an axis-specific name; this store
        keeps one name for both, so those two are mapped and everything else
        resolves to the attribute of the same name.
        """
        if key in _NODE_KEY_COLUMNS:
            return self.node_key
        return getattr(self, key)


@dataclass
class _GraphState:
    """One named graph: two dicts and a count of the handles open on it.

    Both dicts are flat. ``nodes`` is keyed ``(tenant_id, kind, node_key)`` and
    ``claims`` is keyed ``(tenant_id, kind, node_key, claim_id)``, so tenant
    scope and compound uniqueness are properties of the key rather than of a
    nesting level someone has to remember to descend. Insertion order is
    arrival order, which is this store's tiebreaker when two claims share an
    observed time.
    """

    nodes: dict[tuple[str, str, str], _Node] = field(default_factory=dict)
    claims: dict[tuple[str, str, str, str], _Claim] = field(default_factory=dict)
    handles: int = 0


#: Named graphs live for as long as some store is open on them. Process-scoped
#: state, and the reason it exists is :attr:`DemoGraphStore.graph_identity`: an
#: identity derived from a name is only honest if the name selects one graph.
#: A per-instance dict would make two handles on one name claim to be the same
#: graph while holding different state, which would turn the single-writer
#: refusal into a false positive.
_GRAPHS: dict[str, _GraphState] = {}


def _attach(graph_name: str) -> _GraphState:
    """Open a handle on the named graph, creating it if it is new."""
    state = _GRAPHS.get(graph_name)
    if state is None:
        state = _GraphState()
        _GRAPHS[graph_name] = state
    state.handles += 1
    return state


def _detach(graph_name: str) -> None:
    """Release one handle, discarding the graph when the last one closes.

    An in-process graph does not outlive the stores open on it. Discarding on
    the last close is what keeps a long test session from accumulating every
    graph it ever booted, and it is the analogue of a temporary file going away
    rather than of a database being dropped.
    """
    state = _GRAPHS.get(graph_name)
    if state is None:
        return
    state.handles -= 1
    if state.handles <= 0:
        del _GRAPHS[graph_name]


def _current_at(claim: _Claim, *, boundary: str) -> bool:
    """The as-of row filter, over canonical text.

    The one place this store expresses "as of" itself: a claim survives when it
    was observed at or before the boundary and was either never superseded or
    superseded after it. Canonical RFC3339 text sorts chronologically, so this
    is a string comparison.

    The other two as-of rules — lineage at the boundary and the supersession
    edge as it stood at the boundary — are deliberately absent here. They live
    in the shared materialization core, which is what stops an adapter forking
    them.
    """
    if claim.observed_at > boundary:
        return False
    return claim.superseded_at is None or claim.superseded_at > boundary


class DemoGraphStore:
    """State and identity owner for the demo adapter.

    Satisfies :class:`ccf.graph.registry.BackendStore` structurally: it offers
    an identity, a reader, and a close. It offers no way to write — every
    mutation lives in :mod:`ccf_demo_adapter.demo_write`, which is the same
    arrangement every in-tree adapter observes and the reason a reader can be
    handed to anyone.

    Args:
        graph_name: Which graph this store opens. Two stores on one name are
            two handles on one graph; two names are two graphs.
    """

    def __init__(self, *, graph_name: str) -> None:
        self._graph_name = graph_name
        self._graph_identity = f"{IDENTITY_SCHEME}{graph_name}"
        self._state = _attach(graph_name)
        self._reader = DemoGraphReader(self)
        self._closed = False

    @property
    def graph_identity(self) -> str:
        """Stable identity of the graph this store is open on.

        The single-writer boot check keys on this. It is derived from the
        supplied name and nothing else — not from the instance — so two handles
        on one graph agree and two graphs differ, which is what makes a second
        boot's refusal a real refusal rather than an artefact.

        ``tenant_id`` is deliberately not part of it. The writer is per-graph,
        never per-tenant, and a tenant-suffixed identity would let two writers
        coexist over one graph by naming different tenants.
        """
        return self._graph_identity

    @property
    def state(self) -> _GraphState:
        """The dicts themselves — the write module's handle on this graph.

        Reachable in principle by any importer, which is why the mutations are
        confined to the write module rather than merely the handle to them. The
        honest claim is the SDK's own: no unforced path exists.
        """
        return self._state

    @property
    def reader(self) -> DemoGraphReader:
        """The read-only view of this graph."""
        return self._reader

    def close(self) -> None:
        """Release this handle on the graph. Idempotent."""
        if self._closed:
            return
        self._closed = True
        _detach(self._graph_name)

    def __enter__(self) -> DemoGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class DemoGraphReader:
    """``GraphReader`` over the demo store's dicts — no query engine, declared.

    Structurally conforms to :class:`ccf.graph.protocols.GraphReader`. Every
    answer takes the same route: acquire the rows this store can narrow
    natively (tenant scope and the as-of row filter), materialize them through
    the shared core, hand them to the shared fallback for the query's predicate
    families and survivor set, and freeze through the interface's ordering
    (`GQ-22` at docs/GRAPH_QUERY_SEMANTICS.md:461).

    There is no translation branch and there will not be one. Declining is a
    first-class outcome (`GQ-29` at docs/GRAPH_QUERY_SEMANTICS.md:554), and a
    partial translation is not an available third option — a translation
    answers the whole query or does not answer at all.
    """

    def __init__(self, store: DemoGraphStore) -> None:
        self._store = store

    def _lineage_rows_for(self, tenant_id: str) -> _LineageRowsFor:
        """A lineage supplier over this graph's claims.

        Returns *rows*, never lineage: the boundary rendering of what comes
        back happens inside the shared core and cannot be reimplemented here.
        Where a SQL adapter closes over a statement, this closes over a dict
        lookup — the lineage sits on the claim record itself.
        """
        state = self._store.state

        def rows_for(kind: str, node_key: str, claim_id: str) -> Sequence[Row]:
            claim = state.claims.get((tenant_id, kind, node_key, claim_id))
            if claim is None:
                return ()
            return tuple({"entry_json": text} for text in claim.lineage.values())

        return rows_for

    def _claims_of(self, *, tenant_id: str, kind: str) -> tuple[_Claim, ...]:
        """Every claim this graph holds on one axis for one tenant."""
        return tuple(
            claim
            for (claim_tenant, claim_kind, _node, _id), claim in (
                self._store.state.claims.items()
            )
            if claim_tenant == tenant_id and claim_kind == kind
        )

    def _chain_of(
        self, *, tenant_id: str, kind: str, node_key: str
    ) -> tuple[_Claim, ...]:
        """One node's whole claim chain, oldest first, ties by arrival.

        A stable sort over dict insertion order, which is this store's arrival
        order — the dict rendering of ordering by observed time with the row
        identifier as tiebreaker.
        """
        return tuple(
            sorted(
                (
                    claim
                    for (
                        claim_tenant,
                        claim_kind,
                        claim_node,
                        _id,
                    ), claim in self._store.state.claims.items()
                    if claim_tenant == tenant_id
                    and claim_kind == kind
                    and claim_node == node_key
                ),
                key=lambda claim: claim.observed_at,
            )
        )

    def query(self, q: GraphQuery) -> GraphView:
        """Answer ``q`` through the shared degrade path — always.

        An empty answer is an answer, never an error (`GQ-23` at
        docs/GRAPH_QUERY_SEMANTICS.md:474). Tenant scope arrives inside the
        frozen value and ``q.as_of`` arrives as data, so this method reads no
        clock.
        """
        boundary = canonical_timestamp(q.as_of)
        entity_rows: tuple[Row, ...] = tuple(
            claim
            for claim in self._claims_of(tenant_id=q.tenant_id, kind=ENTITY_KIND)
            if _current_at(claim, boundary=boundary)
        )
        relationship_rows: tuple[Row, ...] = tuple(
            claim
            for claim in self._claims_of(
                tenant_id=q.tenant_id, kind=RELATIONSHIP_KIND
            )
            if _current_at(claim, boundary=boundary)
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

        Defined as the degenerate everything-question rather than implemented
        beside it (`GQ-21` at docs/GRAPH_QUERY_SEMANTICS.md:446), so the two
        cannot answer differently.
        """
        return self.query(GraphQuery(tenant_id=tenant_id, as_of=at))

    @property
    def attestation(self) -> SourceAttestation:
        """Tier 1 — this is the live graph, whatever it is stored in.

        Policy bindings were stamped by the fabric's own L2 at assembly time
        and lineage is the graph's own accumulated L, with no federation peer
        involved. Persistence is not an attestation dimension, so a dict store
        reports exactly what a database-backed one reports.
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
        rows = self._chain_of(
            tenant_id=tenant_id, kind=ENTITY_KIND, node_key=entity_uri
        )
        return _entity_records(
            rows, lineage_rows_for=self._lineage_rows_for(tenant_id)
        )

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        """Return every claim ever made about one edge, oldest first."""
        rows = self._chain_of(
            tenant_id=tenant_id,
            kind=RELATIONSHIP_KIND,
            node_key=relationship_key,
        )
        return _relationship_records(
            rows, lineage_rows_for=self._lineage_rows_for(tenant_id)
        )
