"""Backend-neutral materialization of persisted rows into typed records.

Whitepaper §7.3 (the Context Graph as first-class persisted state) and
INV-CH7-14 (an as-of read re-renders the state the fabric held at ``at``,
with no future information leaking in). DESIGN.md §2A.5.2.

**Why this module exists.** The bitemporal read has three places where "as of"
has to be honoured — the row filter, the lineage set, and the supersession edge
— and only the first of them is expressible in SQL. If each backend carried its
own copy of the other two, the D-16 conformance suite would be asserting that
two independent implementations of the same subtle rule happened to agree, and
the day they stopped agreeing the suite would report a Postgres bug rather than
a divergence. So the SQL is per dialect and everything *above* the rows is
shared: a backend supplies five statements and a way to run them, and gets the
whole ``GraphReader`` surface.

**The shape of the sharing.** Adapters answer rows; the core —
:func:`materialize_view` — materializes, orders, freezes (locked roadmap
constraint 3: ordering and serialization belong to the interface, never to an
adapter). Any source whose rows satisfy :class:`Row` (a plain ``dict`` does)
feeds the core the same way the SQL layer below does: two row sets plus a
lineage supplier. A non-SQL backend therefore CANNOT re-implement
lineage-at-boundary or supersession-as-of, because those rules live only here
and no row source reaches a ``GraphView`` around them — which is exactly the
per-adapter materialization fork this shape exists to prevent
(15.2-RESEARCH.md Pitfall 5).

There is no way to write from here, by construction — see
``ccf.graph.backends.sqlite`` for why that absence is load-bearing.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, ClassVar, Protocol

from ccf.contracts.canonical import canonical_timestamp
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph import fallback
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    RelationshipRecord,
    SourceAttestation,
)

__ccf_mode__ = "algorithmic"

__all__ = ["ENTITY_KIND", "RELATIONSHIP_KIND", "BaseGraphReader", "Row", "parse_timestamp"]

# Discriminators for the shared lineage table. Vocabulary of the graph tier.
ENTITY_KIND = "entity"
RELATIONSHIP_KIND = "relationship"


class Row(Protocol):
    """A column-addressable result row.

    ``sqlite3.Row``, psycopg's ``dict_row``, and a plain ``dict`` all satisfy
    this; nothing in the shared read path needs to know which it has.
    """

    def __getitem__(self, key: str, /) -> Any: ...


#: Supplies one claim's lineage rows, keyed on ``(kind, node_key, claim_id)``.
#: Tenant scope is the supplier's own concern: the SQL client closes over the
#: tenant it is reading for; a dict-backed source indexes however it likes.
#: The supplier only *acquires* rows — the lineage-at-boundary rendering of
#: what it returns happens in the core and nowhere else.
_LineageRowsFor = Callable[[str, str, str], Sequence[Row]]


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse a canonical RFC3339 UTC timestamp back into a ``datetime``.

    Both reference backends store timestamps as canonical text
    (:func:`ccf.contracts.canonical.canonical_timestamp`) rather than as a
    native timestamp type. That is deliberate: a native column would round-trip
    at whatever precision the substrate happens to keep, and the conformance
    suite compares canonical bytes across substrates (04-RESEARCH.md Pitfall 3).
    One rendering, produced by the canonical serializer, is what makes the two
    backends byte-identical instead of merely similar.
    """
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _lineage_at_boundary(
    rows: Sequence[Row], *, boundary: datetime | None
) -> frozenset[LineageEntry]:
    """Render a claim's lineage as it stood at ``boundary``.

    L accumulates by set-union over a claim's life (INV-CH7-17), so a claim
    current in March can pick up corroborating evidence in July. Under
    INV-CH7-14 that evidence must not appear in a March view: an entry the
    fabric had not received yet is future information exactly as a
    later-superseding claim is. ``boundary`` of ``None`` means a history
    read, where the whole accumulated set is the answer.

    This is the lineage-at-boundary rule, and this function is the only place
    it exists. Row *acquisition* is deliberately the caller's problem — a
    substrate hands rows in, so no substrate can bury a divergent copy of the
    boundary filter inside its own lineage query (15.2-RESEARCH.md Pitfall 5).
    """
    entries = (
        LineageEntry.model_validate(json.loads(row["entry_json"])) for row in rows
    )
    if boundary is None:
        return frozenset(entries)
    return frozenset(entry for entry in entries if entry.observed_at <= boundary)


def _supersession_as_of(
    row: Row, *, boundary: datetime | None
) -> tuple[str | None, datetime | None]:
    """Render the supersession edge as it stood at ``boundary``.

    INV-CH7-14 is explicit that an as-of read re-renders the state the
    fabric held at ``at``, and that *claims superseded later are still
    current*. The row filter already keeps such a claim in the view; this
    keeps its supersession edge out of it. Without this, a claim read as of
    March would carry a pointer to the claim that replaced it in July —
    future information, leaking through the one field the temporal filter
    does not cover, and enough to change the content hash of a view that is
    supposed to be identical to the one the decision saw.

    ``boundary`` is ``None`` for history reads, where the whole supersession
    chain is the answer being asked for.
    """
    superseded_at = parse_timestamp(row["superseded_at"])
    if (
        boundary is not None
        and superseded_at is not None
        and superseded_at > boundary
    ):
        return None, None
    return row["superseded_by"], superseded_at


def _entity_records(
    rows: Sequence[Row],
    *,
    lineage_rows_for: _LineageRowsFor,
    boundary: datetime | None = None,
) -> tuple[EntityRecord, ...]:
    """Build entity records from rows, rendering both boundary rules."""
    records: list[EntityRecord] = []
    for row in rows:
        payload: dict[str, Any] = json.loads(row["claim_json"])
        payload["lineage"] = [
            entry.model_dump(mode="json")
            for entry in _lineage_at_boundary(
                lineage_rows_for(ENTITY_KIND, row["entity_uri"], row["claim_id"]),
                boundary=boundary,
            )
        ]
        superseded_by, superseded_at = _supersession_as_of(row, boundary=boundary)
        records.append(
            EntityRecord(
                claim_id=row["claim_id"],
                claim=EntityClaim.model_validate(payload),
                policy_bundle_version=row["policy_bundle_version"],
                superseded_by=superseded_by,
                superseded_at=superseded_at,
            )
        )
    return tuple(records)


def _relationship_records(
    rows: Sequence[Row],
    *,
    lineage_rows_for: _LineageRowsFor,
    boundary: datetime | None = None,
) -> tuple[RelationshipRecord, ...]:
    """Build relationship records from rows, rendering both boundary rules."""
    records: list[RelationshipRecord] = []
    for row in rows:
        payload: dict[str, Any] = json.loads(row["claim_json"])
        payload["lineage"] = [
            entry.model_dump(mode="json")
            for entry in _lineage_at_boundary(
                lineage_rows_for(
                    RELATIONSHIP_KIND, row["relationship_key"], row["claim_id"]
                ),
                boundary=boundary,
            )
        ]
        superseded_by, superseded_at = _supersession_as_of(row, boundary=boundary)
        records.append(
            RelationshipRecord(
                relationship_key=row["relationship_key"],
                claim_id=row["claim_id"],
                claim=RelationshipClaim.model_validate(payload),
                policy_bundle_version=row["policy_bundle_version"],
                superseded_by=superseded_by,
                superseded_at=superseded_at,
            )
        )
    return tuple(records)


def _ordered_view(
    *,
    tenant_id: str,
    as_of: datetime,
    entities: Sequence[EntityRecord],
    relationships: Sequence[RelationshipRecord],
) -> GraphView:
    """Freeze records into the deterministically ordered ``GraphView``.

    Ordering belongs to the interface, never to an answerer (`GQ-22` at
    docs/GRAPH_QUERY_SEMANTICS.md:461) — entities by ``entity_uri``,
    relationships by ``relationship_key``, stable sort. This helper is the
    one place the ordering convention exists: :func:`materialize_view`
    freezes materialized rows through it, and
    :meth:`BaseGraphReader.query` freezes the fallback's answer through it,
    so two answerers' identical record sets can never hash differently.
    """
    return GraphView(
        tenant_id=tenant_id,
        as_of=as_of,
        entities=tuple(
            sorted(entities, key=lambda record: record.claim.entity_uri)
        ),
        relationships=tuple(
            sorted(relationships, key=lambda record: record.relationship_key)
        ),
    )


def materialize_view(
    *,
    entity_rows: Sequence[Row],
    relationship_rows: Sequence[Row],
    tenant_id: str,
    as_of: datetime,
    lineage_rows_for: _LineageRowsFor,
) -> GraphView:
    """Materialize an as-of ``GraphView`` from any Row-Protocol source.

    The substrate-neutral core of the read path: rows in, ordered frozen
    records out. ``entity_rows`` and ``relationship_rows`` are the claims
    current at ``as_of`` under the row filter the *source* applied — the one
    "as of" place a substrate can express natively. The other two places are
    rendered here and only here: the lineage set via the lineage-at-boundary
    rule (:func:`_lineage_at_boundary`) and the supersession edge via the
    supersession-as-of rule (:func:`_supersession_as_of`), so no row source
    can fork them (15.2-RESEARCH.md Pitfall 5).

    Ordering is applied here, never trusted from the source (locked roadmap
    constraint 3): entities by ``entity_uri``, relationships by
    ``relationship_key`` — the :class:`ccf.graph.protocols.GraphView`
    determinism contract. A source that answers rows in arbitrary order
    materializes the same canonical bytes as one that answers them sorted.
    The sort is stable, so a source that pre-sorts (the backends' as-of
    ``ORDER BY``) renders byte-identically to what it rendered before this
    core existed.

    ``lineage_rows_for`` supplies one claim's lineage rows given
    ``(kind, node_key, claim_id)``: the SQL client passes a closure over its
    lineage statement; a dict-backed source passes an index lookup.

    Graph-tier internal API: deliberately not exported via ``__all__`` and
    absent from the public-surface manifest. Its callers are graph-tier
    adapters inside ``ccf.graph``; the public read surface remains
    :class:`ccf.graph.protocols.GraphReader`.
    """
    entities = _entity_records(
        entity_rows, lineage_rows_for=lineage_rows_for, boundary=as_of
    )
    relationships = _relationship_records(
        relationship_rows, lineage_rows_for=lineage_rows_for, boundary=as_of
    )
    return _ordered_view(
        tenant_id=tenant_id,
        as_of=as_of,
        entities=entities,
        relationships=relationships,
    )


class BaseGraphReader:
    """The shared ``GraphReader`` implementation over any SQL backend.

    Structurally conforms to :class:`ccf.graph.protocols.GraphReader`; there is
    no method here that mutates state, and that absence is the point (DESIGN.md
    §2A.5.3 layer 1).

    A concrete backend supplies the five statements below in its own dialect
    and implements :meth:`_query`. Everything else — lineage set-union
    rendering, the supersession-as-of rule, record construction, view ordering
    — lives in the module-level materialization core this class is one client
    of, so the semantics cannot drift between substrates: the SQL layer
    acquires rows and hands them to :func:`materialize_view` with a lineage
    supplier closed over :attr:`SELECT_LINEAGE`.
    """

    #: Lineage entries for one claim, keyed on (tenant, kind, node, claim).
    SELECT_LINEAGE: ClassVar[str]
    #: Every claim ever made about one entity, oldest first.
    SELECT_ENTITY_HISTORY: ClassVar[str]
    #: Every claim ever made about one edge, oldest first.
    SELECT_RELATIONSHIP_HISTORY: ClassVar[str]
    #: Entity claims current at an observed-time boundary.
    SELECT_ENTITIES_AS_OF: ClassVar[str]
    #: Relationship claims current at an observed-time boundary.
    SELECT_RELATIONSHIPS_AS_OF: ClassVar[str]

    # Telemetry counters. Class-level zeros so no subclass ``__init__``
    # cooperation is required; ``+=`` writes an instance attribute, so the
    # counts are per-reader-instance from the first answer on.
    _translated_answers: int = 0
    _fallback_answers: int = 0

    def _query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        """Run one parameterized read and return its rows."""
        raise NotImplementedError

    def _lineage_rows_for(self, tenant_id: str) -> _LineageRowsFor:
        """A lineage supplier closing over this reader's dialect and tenant.

        The one place SQL acquisition of lineage rows lives. What comes back
        is *rows*, not lineage: the boundary rendering of those rows happens
        in :func:`_lineage_at_boundary`, which this closure feeds and cannot
        reimplement.
        """

        def rows_for(kind: str, node_key: str, claim_id: str) -> Sequence[Row]:
            return self._query(
                self.SELECT_LINEAGE, (tenant_id, kind, node_key, claim_id)
            )

        return rows_for

    def _translate_query(
        self, q: GraphQuery
    ) -> tuple[Sequence[Row], Sequence[Row]] | None:
        """The substrate-translation hook — whole query or ``None``.

        The contract is `GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583,
        verbatim: a translation answers the **whole query or does not
        answer at all**. A non-``None`` return is the pair
        ``(entity_rows, relationship_rows)`` constituting the complete
        answer's row set — every predicate family applied, hop
        admissibility applied, ``allowed_entities`` membership applied.
        ``None`` means the baseline acquisition runs and the fallback
        enforces the whole query. There is no protocol by which a
        translation reports "I applied the policy family but not the
        traverse family" — no partial-family bookkeeping exists, because
        such bookkeeping is precisely the per-substrate divergence surface
        the semantics document exists to close. The hook has exactly two
        outcomes; the default is ``None``.

        Under a declined translation the baseline acquisition MUST apply
        tenant + as-of narrowing, MAY additionally narrow by predicates
        entailed by the query's policy/temporal families and by
        ``allowed_entities`` membership — safe narrowing per `GQ-33` at
        docs/GRAPH_QUERY_SEMANTICS.md:594, sound because the fallback
        re-enforces the whole query over whatever arrives — and MUST NOT
        narrow by the traverse family: reachability is a whole-graph
        property, and a row-level proxy for it starves the walk of the
        state it must expand over.
        """
        del q  # the base holds no native translation; adapters may.
        return None

    def query(self, q: GraphQuery) -> GraphView:
        """Answer ``q`` — translated where the substrate can, degraded where not.

        The template method of the read seam (D-04): ask
        :meth:`_translate_query` for a whole-query answer; when it
        declines, acquire the tenant- and as-of-narrowed rows through the
        two existing ``SELECT_*_AS_OF`` statements, materialize them
        through the substrate-neutral core (:func:`materialize_view` —
        the only place canonical record bytes are produced), and apply
        :func:`ccf.graph.fallback.answer` for the query's predicate
        families and ``allowed_entities``. Either way the answer freezes
        through the interface's ordering (`GQ-22` at
        docs/GRAPH_QUERY_SEMANTICS.md:461).

        An empty answer is an answer, never an error (`GQ-23` at
        docs/GRAPH_QUERY_SEMANTICS.md:474). Tenant scope arrives inside
        the frozen value; ``q.as_of`` arrives as data — this method reads
        no clock.

        **A classification query carries the boot-minted authority, or it is
        refused before any substrate I/O** (SEC-023; ``D-IMPL-374``): the
        check is
        :func:`~ccf.graph.protocols.require_query_classification_authority`,
        and a query with no classification map passes it untouched.

        Raises:
            ClassificationAuthorityMissing: ``q`` sets
                ``classification_attribute_by_class`` and carries no
                classification authority — a reader reached without
                ``ccf.boot.boot`` has none to offer (SEC-023; ``D-IMPL-374``).
            ClassificationAuthorityNotMinted: ``q``'s authority was not minted
                by ``ccf.boot.boot`` (built by hand, or rebuilt).
            UngovernedClassificationAttribute: ``q``'s authority does not
                cover an attribute its classification map names.
        """
        # SEC-023 (`D-IMPL-374`): a classification query carries the authority a
        # booted fabric's reader checked it against, or it is refused here.
        from ccf.graph.protocols import require_query_classification_authority

        require_query_classification_authority(q)
        translated = self._translate_query(q)
        lineage_rows_for = self._lineage_rows_for(q.tenant_id)
        if translated is not None:
            entity_rows, relationship_rows = translated
            self._translated_answers += 1
            return materialize_view(
                entity_rows=entity_rows,
                relationship_rows=relationship_rows,
                tenant_id=q.tenant_id,
                as_of=q.as_of,
                lineage_rows_for=lineage_rows_for,
            )
        boundary = canonical_timestamp(q.as_of)
        entity_rows = self._query(
            self.SELECT_ENTITIES_AS_OF, (q.tenant_id, boundary, boundary)
        )
        relationship_rows = self._query(
            self.SELECT_RELATIONSHIPS_AS_OF, (q.tenant_id, boundary, boundary)
        )
        materialized = materialize_view(
            entity_rows=entity_rows,
            relationship_rows=relationship_rows,
            tenant_id=q.tenant_id,
            as_of=q.as_of,
            lineage_rows_for=lineage_rows_for,
        )
        entities, relationships = fallback.answer(
            materialized.entities, materialized.relationships, query=q
        )
        self._fallback_answers += 1
        return _ordered_view(
            tenant_id=q.tenant_id,
            as_of=q.as_of,
            entities=entities,
            relationships=relationships,
        )

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        """Return the state ``tenant_id``'s graph held at observed-time ``at``.

        The D-07 derivation: ``as_of`` is **defined** as the degenerate
        everything-question — `GQ-21` at
        docs/GRAPH_QUERY_SEMANTICS.md:446. Identical records, identical
        ordering, identical canonical bytes; every existing call site
        remains valid unchanged.
        """
        return self.query(GraphQuery(tenant_id=tenant_id, as_of=at))

    @property
    def attestation(self) -> SourceAttestation:
        """Tier 1 — the live graph's well-known attestation value (D-09).

        SDK-defined per CLAUDE.md §11: policy bindings were stamped by the
        fabric's own L2 at assembly time and lineage is the graph's own
        accumulated L, with no federation peer involved.
        """
        return SourceAttestation(
            policy_binding="assembly-stamped",
            lineage="graph-supplied",
            peer=None,
        )

    @property
    def translated_answers(self) -> int:
        """How many ``query()`` answers the substrate translation produced.

        Deliberately outside the replay record: what was natively
        translated versus scanned is telemetry, and performance is never a
        replay input (D-04; `GQ-34` at docs/GRAPH_QUERY_SEMANTICS.md:609).
        Reset semantics: counters are per-reader-instance and monotonic
        for the instance's lifetime, never reset; per-execution
        attribution is the deployment's subtraction to make. Exposed as an
        observable counter for tests and operators, the
        ``IntermediateCache.hits`` precedent — an effect that cannot be
        observed cannot be shown to be sound.
        """
        return self._translated_answers

    @property
    def fallback_answers(self) -> int:
        """How many ``query()`` answers the internal degrade path produced.

        Same discipline as :attr:`translated_answers`: telemetry outside
        the replay record (D-04), per-reader-instance, monotonic for the
        instance's lifetime, never reset.
        """
        return self._fallback_answers

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        """Return every claim ever made about ``entity_uri``, oldest first."""
        rows = self._query(self.SELECT_ENTITY_HISTORY, (tenant_id, entity_uri))
        return _entity_records(
            rows, lineage_rows_for=self._lineage_rows_for(tenant_id)
        )

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        """Return every claim ever made about one edge, oldest first."""
        rows = self._query(
            self.SELECT_RELATIONSHIP_HISTORY, (tenant_id, relationship_key)
        )
        return _relationship_records(
            rows, lineage_rows_for=self._lineage_rows_for(tenant_id)
        )
