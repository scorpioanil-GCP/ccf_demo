"""SQLite reference ``GraphStore`` — schema, connection, and the read path.

Whitepaper §7.3 (the Context Graph as first-class persisted state); DESIGN.md
§2A.5.2 (the D-IMPL-34 semantics) and D-IMPL-02 (SQLite as the development
reference backend, load-bearing for the §9 examples discipline).

**What this module deliberately does not contain: any way to write.**
:class:`SqliteGraphStore` owns the connection and the schema; the read path is
here; every ``INSERT`` and every supersession ``UPDATE`` lives in
``ccf.graph._writer``, which the CINV-02 lint confines to ``ccf.assembly`` and
``ccf.boot``. Putting a "convenience" write helper here would hand a write path
to every module that legitimately needs to read (04-RESEARCH.md anti-patterns).

**Physical layout.** Five tables, none of them normative — the whitepaper's
"~10 collections" is reference grounding, not a count to match:

``entities`` / ``relationships``
    Node and edge identity. ``UNIQUE (tenant_id, entity_uri)`` puts compound
    uniqueness *at the persistence tier*, where a concurrent second writer or a
    buggy caller still cannot get around it — application-layer uniqueness
    checks are advisory in a way an index is not (INV-CH7-16).

``entity_claims`` / ``relationship_claims``
    Append-only claim history. Rows are never deleted and their content is
    never updated; the only columns that change after insert are
    ``superseded_by`` / ``superseded_at``, which is what supersession *is*
    (INV-CH7-04, INV-CH7-21). Keeping identity and history in separate tables
    is what lets both "one node per ``(tenant, uri)``" and "every claim ever
    made survives" be true simultaneously.

``lineage``
    Append-only child table keyed on the full lineage-entry identity, giving L
    set-union semantics for free: a re-delivered envelope collides and is
    ignored, a second source does not (INV-CH7-17).

Timestamps are stored as canonical RFC3339 UTC text
(:func:`ccf.contracts.canonical.canonical_timestamp`) so ordering comparisons
in SQL are chronological and so the text a backend stores is the same text the
canonical serializer produces.

Every statement is parameterized. There is no f-string SQL in this module and
none may be added: string-built SQL is how tenant scoping becomes bypassable.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from ccf.contracts.canonical import canonical_timestamp
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.protocols import EntityRecord, GraphView, RelationshipRecord

__ccf_mode__ = "algorithmic"

__all__ = ["ENTITY_KIND", "RELATIONSHIP_KIND", "SqliteGraphReader", "SqliteGraphStore"]

# Discriminators for the shared lineage table. Vocabulary of this module only.
ENTITY_KIND = "entity"
RELATIONSHIP_KIND = "relationship"

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS entities (
        tenant_id TEXT NOT NULL,
        entity_uri TEXT NOT NULL,
        entity_class TEXT NOT NULL,
        first_observed_at TEXT NOT NULL,
        last_observed_at TEXT NOT NULL,
        UNIQUE (tenant_id, entity_uri)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entity_claims (
        tenant_id TEXT NOT NULL,
        entity_uri TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        claim_json TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        policy_bundle_version TEXT NOT NULL,
        superseded_by TEXT,
        superseded_at TEXT,
        PRIMARY KEY (tenant_id, entity_uri, claim_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationships (
        tenant_id TEXT NOT NULL,
        relationship_key TEXT NOT NULL,
        relationship_type TEXT NOT NULL,
        subject_uri TEXT NOT NULL,
        object_uri TEXT NOT NULL,
        first_observed_at TEXT NOT NULL,
        last_observed_at TEXT NOT NULL,
        UNIQUE (tenant_id, relationship_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationship_claims (
        tenant_id TEXT NOT NULL,
        relationship_key TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        claim_json TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        policy_bundle_version TEXT NOT NULL,
        superseded_by TEXT,
        superseded_at TEXT,
        PRIMARY KEY (tenant_id, relationship_key, claim_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lineage (
        tenant_id TEXT NOT NULL,
        claim_kind TEXT NOT NULL,
        node_key TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        lineage_id TEXT NOT NULL,
        entry_json TEXT NOT NULL,
        PRIMARY KEY (tenant_id, claim_kind, node_key, claim_id, lineage_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_entity_claims_observed
        ON entity_claims (tenant_id, observed_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_relationship_claims_observed
        ON relationship_claims (tenant_id, observed_at)
    """,
)

_SELECT_LINEAGE = """
    SELECT entry_json FROM lineage
    WHERE tenant_id = ? AND claim_kind = ? AND node_key = ? AND claim_id = ?
"""

_SELECT_ENTITY_HISTORY = """
    SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
           superseded_by, superseded_at
    FROM entity_claims
    WHERE tenant_id = ? AND entity_uri = ?
    ORDER BY observed_at, rowid
"""

_SELECT_RELATIONSHIP_HISTORY = """
    SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
           superseded_by, superseded_at
    FROM relationship_claims
    WHERE tenant_id = ? AND relationship_key = ?
    ORDER BY observed_at, rowid
"""

# The bitemporal read. `observed_at <= ?` excludes what the fabric had not yet
# learned at the read boundary; the supersession clause keeps a claim current
# until the instant it was superseded. Together: no future information leaks
# into a historical view (INV-CH7-14).
_SELECT_ENTITIES_AS_OF = """
    SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
           superseded_by, superseded_at
    FROM entity_claims
    WHERE tenant_id = ?
      AND observed_at <= ?
      AND (superseded_at IS NULL OR superseded_at > ?)
    ORDER BY entity_uri
"""

_SELECT_RELATIONSHIPS_AS_OF = """
    SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
           superseded_by, superseded_at
    FROM relationship_claims
    WHERE tenant_id = ?
      AND observed_at <= ?
      AND (superseded_at IS NULL OR superseded_at > ?)
    ORDER BY relationship_key
"""


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SqliteGraphStore:
    """Connection and schema owner for the SQLite reference backend.

    Args:
        database_path: File to open. A distinct path per fabric is what makes
            "one writer per graph" a checkable statement at boot.

    The store is *not* a ``GraphStore`` in the sense of offering both halves of
    the Protocol: it offers :attr:`reader` and, to the writer module alone, the
    connection. See the module docstring.
    """

    def __init__(self, *, database_path: Path | str) -> None:
        self._database_path = str(database_path)
        self._connection = sqlite3.connect(self._database_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA foreign_keys = ON")
        with self._connection:
            for statement in _SCHEMA:
                self._connection.execute(statement)
        self._reader = SqliteGraphReader(self._connection)

    @property
    def graph_identity(self) -> str:
        """Stable identity of the persisted graph this store is attached to.

        The single-writer boot check keys on this: two writers over two
        different databases are two fabrics, while two writers over the same
        database are the violation.
        """
        return self._database_path

    @property
    def reader(self) -> SqliteGraphReader:
        """The read-only view of this graph — safe to hand to anyone."""
        return self._reader

    @property
    def connection(self) -> sqlite3.Connection:
        """The raw connection.

        Reachable in principle by any importer, which is why the write
        *statements* — not merely the handle — live behind the CINV-02 lint.
        The honest claim is DESIGN.md §9's: no unforced path exists, and every
        forced path fails CI or fails at boot.
        """
        return self._connection

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SqliteGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class SqliteGraphReader:
    """``GraphReader`` implementation over a SQLite connection.

    Structurally conforms to :class:`ccf.graph.protocols.GraphReader`; there is
    no method here that mutates state, and that absence is the point (DESIGN.md
    §2A.5.3 layer 1).
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

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
        rows = self._connection.execute(
            _SELECT_LINEAGE, (tenant_id, kind, node_key, claim_id)
        ).fetchall()
        entries = (
            LineageEntry.model_validate(json.loads(row["entry_json"])) for row in rows
        )
        if boundary is None:
            return frozenset(entries)
        return frozenset(entry for entry in entries if entry.observed_at <= boundary)

    @staticmethod
    def _supersession_as_of(
        row: sqlite3.Row, *, boundary: datetime | None
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
        superseded_at = _parse_timestamp(row["superseded_at"])
        if (
            boundary is not None
            and superseded_at is not None
            and superseded_at > boundary
        ):
            return None, None
        return row["superseded_by"], superseded_at

    def _entity_records(
        self,
        rows: Iterable[sqlite3.Row],
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
        rows: Iterable[sqlite3.Row],
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
        entity_rows = self._connection.execute(
            _SELECT_ENTITIES_AS_OF, (tenant_id, boundary, boundary)
        ).fetchall()
        relationship_rows = self._connection.execute(
            _SELECT_RELATIONSHIPS_AS_OF, (tenant_id, boundary, boundary)
        ).fetchall()
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
        rows = self._connection.execute(
            _SELECT_ENTITY_HISTORY, (tenant_id, entity_uri)
        ).fetchall()
        return self._entity_records(rows, tenant_id=tenant_id)

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        """Return every claim ever made about one edge, oldest first."""
        rows = self._connection.execute(
            _SELECT_RELATIONSHIP_HISTORY, (tenant_id, relationship_key)
        ).fetchall()
        return self._relationship_records(rows, tenant_id=tenant_id)
