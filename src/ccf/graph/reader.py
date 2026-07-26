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

There is no way to write from here, by construction — see
``ccf.graph.backends.sqlite`` for why that absence is load-bearing.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any, ClassVar, Protocol

from ccf.contracts.canonical import canonical_timestamp
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.protocols import EntityRecord, GraphView, RelationshipRecord

__ccf_mode__ = "algorithmic"

__all__ = ["ENTITY_KIND", "RELATIONSHIP_KIND", "BaseGraphReader", "Row", "parse_timestamp"]

# Discriminators for the shared lineage table. Vocabulary of the graph tier.
ENTITY_KIND = "entity"
RELATIONSHIP_KIND = "relationship"


class Row(Protocol):
    """A column-addressable result row.

    ``sqlite3.Row`` and psycopg's ``dict_row`` both satisfy this; nothing in
    the shared read path needs to know which it has.
    """

    def __getitem__(self, key: str, /) -> Any: ...


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


class BaseGraphReader:
    """The shared ``GraphReader`` implementation over any SQL backend.

    Structurally conforms to :class:`ccf.graph.protocols.GraphReader`; there is
    no method here that mutates state, and that absence is the point (DESIGN.md
    §2A.5.3 layer 1).

    A concrete backend supplies the five statements below in its own dialect
    and implements :meth:`_query`. Everything else — lineage set-union
    rendering, the supersession-as-of rule, record construction, view ordering
    — is inherited, so the semantics cannot drift between substrates.
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

    def _query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        """Run one parameterized read and return its rows."""
        raise NotImplementedError

    def _lineage(
        self,
        *,
        tenant_id: str,
        kind: str,
        node_key: str,
        claim_id: str,
        boundary: datetime | None = None,
    ) -> frozenset[LineageEntry]:
        """Return the claim's lineage as it stood at ``boundary``.

        L accumulates by set-union over a claim's life (INV-CH7-17), so a claim
        current in March can pick up corroborating evidence in July. Under
        INV-CH7-14 that evidence must not appear in a March view: an entry the
        fabric had not received yet is future information exactly as a
        later-superseding claim is. ``boundary`` of ``None`` means a history
        read, where the whole accumulated set is the answer.
        """
        rows = self._query(
            self.SELECT_LINEAGE, (tenant_id, kind, node_key, claim_id)
        )
        entries = (
            LineageEntry.model_validate(json.loads(row["entry_json"])) for row in rows
        )
        if boundary is None:
            return frozenset(entries)
        return frozenset(entry for entry in entries if entry.observed_at <= boundary)

    @staticmethod
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
        self,
        rows: Sequence[Row],
        *,
        tenant_id: str,
        boundary: datetime | None = None,
    ) -> tuple[EntityRecord, ...]:
        records: list[EntityRecord] = []
        for row in rows:
            payload: dict[str, Any] = json.loads(row["claim_json"])
            payload["lineage"] = [
                entry.model_dump(mode="json")
                for entry in self._lineage(
                    tenant_id=tenant_id,
                    kind=ENTITY_KIND,
                    node_key=row["entity_uri"],
                    claim_id=row["claim_id"],
                    boundary=boundary,
                )
            ]
            superseded_by, superseded_at = self._supersession_as_of(
                row, boundary=boundary
            )
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
        self,
        rows: Sequence[Row],
        *,
        tenant_id: str,
        boundary: datetime | None = None,
    ) -> tuple[RelationshipRecord, ...]:
        records: list[RelationshipRecord] = []
        for row in rows:
            payload: dict[str, Any] = json.loads(row["claim_json"])
            payload["lineage"] = [
                entry.model_dump(mode="json")
                for entry in self._lineage(
                    tenant_id=tenant_id,
                    kind=RELATIONSHIP_KIND,
                    node_key=row["relationship_key"],
                    claim_id=row["claim_id"],
                    boundary=boundary,
                )
            ]
            superseded_by, superseded_at = self._supersession_as_of(
                row, boundary=boundary
            )
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

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        """Return the state ``tenant_id``'s graph held at observed-time ``at``."""
        boundary = canonical_timestamp(at)
        entity_rows = self._query(
            self.SELECT_ENTITIES_AS_OF, (tenant_id, boundary, boundary)
        )
        relationship_rows = self._query(
            self.SELECT_RELATIONSHIPS_AS_OF, (tenant_id, boundary, boundary)
        )
        return GraphView(
            tenant_id=tenant_id,
            as_of=at,
            entities=self._entity_records(
                entity_rows, tenant_id=tenant_id, boundary=at
            ),
            relationships=self._relationship_records(
                relationship_rows, tenant_id=tenant_id, boundary=at
            ),
        )

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        """Return every claim ever made about ``entity_uri``, oldest first."""
        rows = self._query(self.SELECT_ENTITY_HISTORY, (tenant_id, entity_uri))
        return self._entity_records(rows, tenant_id=tenant_id)

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        """Return every claim ever made about one edge, oldest first."""
        rows = self._query(
            self.SELECT_RELATIONSHIP_HISTORY, (tenant_id, relationship_key)
        )
        return self._relationship_records(rows, tenant_id=tenant_id)
