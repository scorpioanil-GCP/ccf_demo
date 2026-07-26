"""SQLite reference ``GraphStore`` — schema, connection, and the read path.

Whitepaper §7.3 (the Context Graph as first-class persisted state); DESIGN.md
§2A.5.2 (the D-IMPL-34 semantics) and D-IMPL-02 (SQLite as the development
reference backend, load-bearing for the §9 examples discipline).

**What this module deliberately does not contain: any way to write.**
:class:`SqliteGraphStore` owns the connection and the schema; the read path is
here (as five statements handed to :class:`ccf.graph.reader.BaseGraphReader`);
every ``INSERT`` and every supersession ``UPDATE`` lives in
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

import sqlite3
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import ClassVar

from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, BaseGraphReader, Row

__ccf_mode__ = "algorithmic"

__all__ = ["ENTITY_KIND", "RELATIONSHIP_KIND", "SqliteGraphReader", "SqliteGraphStore"]

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


class SqliteGraphReader(BaseGraphReader):
    """``GraphReader`` over a SQLite connection — dialect and rows only.

    The bitemporal rendering rules live in
    :class:`ccf.graph.reader.BaseGraphReader`; what is here is the SQLite
    dialect of the five reads and the connection they run on. ``rowid`` is the
    insertion-order tiebreak within one observed-time instant, which is what
    keeps history ordering total rather than merely chronological.
    """

    # The bitemporal read. `observed_at <= ?` excludes what the fabric had not
    # yet learned at the read boundary; the supersession clause keeps a claim
    # current until the instant it was superseded. Together: no future
    # information leaks into a historical view (INV-CH7-14).
    SELECT_LINEAGE: ClassVar[str] = """
        SELECT entry_json FROM lineage
        WHERE tenant_id = ? AND claim_kind = ? AND node_key = ? AND claim_id = ?
    """
    SELECT_ENTITY_HISTORY: ClassVar[str] = """
        SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM entity_claims
        WHERE tenant_id = ? AND entity_uri = ?
        ORDER BY observed_at, rowid
    """
    SELECT_RELATIONSHIP_HISTORY: ClassVar[str] = """
        SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM relationship_claims
        WHERE tenant_id = ? AND relationship_key = ?
        ORDER BY observed_at, rowid
    """
    SELECT_ENTITIES_AS_OF: ClassVar[str] = """
        SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM entity_claims
        WHERE tenant_id = ?
          AND observed_at <= ?
          AND (superseded_at IS NULL OR superseded_at > ?)
        ORDER BY entity_uri
    """
    SELECT_RELATIONSHIPS_AS_OF: ClassVar[str] = """
        SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM relationship_claims
        WHERE tenant_id = ?
          AND observed_at <= ?
          AND (superseded_at IS NULL OR superseded_at > ?)
        ORDER BY relationship_key
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def _query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        return self._connection.execute(sql, params).fetchall()
