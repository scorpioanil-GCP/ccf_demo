"""Postgres reference ``GraphStore`` — schema, connection, and the read path.

Whitepaper §7.3 (the Context Graph as first-class persisted state); DESIGN.md
§2A.5.2 (the D-IMPL-34 six semantics) and D-IMPL-02 (Postgres as the production
reference backend alongside SQLite-for-dev). Lands after the slice, against the
already-stable conformance suite (D-11/D-16).

**One semantic, two dialects.** This module is the Postgres half of a pair. It
carries no rule the SQLite backend does not also carry; what differs is dialect
(``%s`` placeholders, ``GREATEST``/``LEAST``, ``ON CONFLICT DO NOTHING`` for
the ignore-on-duplicate case, an explicit ``seq`` for insertion order where
SQLite has ``rowid``) and physical layout, which is backend-internal by
D-IMPL-34. Everything above the rows — lineage set-union rendering, the
supersession-as-of rule, view ordering — is inherited from
:class:`ccf.graph.reader.BaseGraphReader`, so the two backends cannot drift
apart in the places the conformance suite is least able to tell them apart.

**Timestamps are stored as canonical RFC3339 UTC text, not ``timestamptz``.**
That is a contract-layer decision, not a Postgres limitation: comparison in the
conformance suite happens on ``canonical_bytes`` of contracts, and a native
timestamp column would round-trip at the substrate's own precision, which is
exactly the cross-backend drift 04-RESEARCH.md Pitfall 3 warns about. Canonical
text sorts chronologically, so the SQL ordering and range predicates are
unaffected.

**What this module deliberately does not contain: any way to write.** As with
the SQLite backend, every ``INSERT`` and every supersession ``UPDATE`` lives in
``ccf.graph._writer`` behind the CINV-02 import restriction. A new backend adds
a writer *class* there; it does not add a writer *module* here.

**Credentials.** The DSN is supplied by the caller (in practice from the
deployment's environment) and is never logged, never embedded in a docstring,
and never reproduced in :attr:`PostgresGraphStore.graph_identity`, which is
built from host/port/database/schema only (threat T-04-24).

Every statement is parameterized. There is no f-string SQL in this module and
none may be added: the one place an identifier must be interpolated — the
schema name in the DDL and in ``search_path`` — goes through
:class:`psycopg.sql.Identifier`, which quotes and escapes it rather than
pasting it (threat T-04-23).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Any, ClassVar

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, BaseGraphReader, Row

__ccf_mode__ = "algorithmic"

__all__ = [
    "ENTITY_KIND",
    "RELATIONSHIP_KIND",
    "DEFAULT_SCHEMA",
    "PostgresGraphReader",
    "PostgresGraphStore",
]

#: Schema the fabric's tables live in when the caller does not say otherwise.
#: A name, not a tuning value — the SDK ships no domain vocabulary (CINV-01).
DEFAULT_SCHEMA = "ccf"

# Mirrors the SQLite layout table for table. `seq BIGSERIAL` replaces SQLite's
# implicit `rowid` as the insertion-order tiebreak within one observed-time
# instant: without a total order, history reads would be chronological but not
# deterministic, and a deterministic view is the precondition for the
# bit-for-bit composition assertions downstream.
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
        seq BIGSERIAL,
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
        seq BIGSERIAL,
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


def _graph_identity(dsn: str, schema: str) -> str:
    """Name the graph a DSN points at, without carrying its credentials.

    The single-writer boot check keys on this string, so it has to be stable
    and it has to distinguish two graphs — but it is also the string that ends
    up in exception messages, which is why the password and user are dropped
    rather than merely "not usually shown".
    """
    info: dict[str, Any] = conninfo_to_dict(dsn)
    host = str(info.get("host") or "localhost")
    port = str(info.get("port") or "5432")
    database = str(info.get("dbname") or "")
    return f"postgres://{host}:{port}/{database}#{schema}"


class PostgresGraphStore:
    """Connection and schema owner for the Postgres reference backend.

    Args:
        dsn: libpq connection string. Supplied by the deployment (typically
            from an environment variable); never committed and never echoed
            back through :attr:`graph_identity`.
        schema: Postgres schema the fabric's tables live in. Distinct schemas
            on one database are distinct graphs, which is what lets a single
            Postgres instance host several fabrics — and what makes the
            single-writer check meaningful per fabric rather than per server.

    As with the SQLite store this is *not* a store offering both halves of the
    Protocol: it offers :attr:`reader`, and the connection to the writer module
    alone.
    """

    def __init__(self, *, dsn: str, schema: str = DEFAULT_SCHEMA) -> None:
        self._graph_identity = _graph_identity(dsn, schema)
        # Autocommit, with write blocks wrapped in explicit transactions. The
        # alternative — psycopg's default implicit transaction — would leave
        # every *read* holding an open snapshot on the shared connection, so a
        # write committed inside a nested `transaction()` would land in a
        # savepoint of a transaction nobody ever commits. Reads here are
        # single-statement and want the latest state; writes say so explicitly.
        self._connection: psycopg.Connection[dict[str, Any]] = psycopg.connect(
            dsn, row_factory=dict_row, autocommit=True
        )
        schema_ident = sql.Identifier(schema)
        with self._connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(schema_ident)
            )
            # Session-level (not SET LOCAL): every later statement on this
            # connection resolves inside the fabric's own schema, so no
            # statement below needs to qualify — or could be tricked into
            # resolving somewhere else.
            cursor.execute(sql.SQL("SET search_path TO {}").format(schema_ident))
            for statement in _SCHEMA:
                cursor.execute(statement.encode())
        self._reader = PostgresGraphReader(self._connection)

    @property
    def graph_identity(self) -> str:
        """Credential-free identity of the graph this store is attached to."""
        return self._graph_identity

    @property
    def reader(self) -> PostgresGraphReader:
        """The read-only view of this graph — safe to hand to anyone."""
        return self._reader

    @property
    def connection(self) -> psycopg.Connection[dict[str, Any]]:
        """The raw connection — see :class:`ccf.graph.backends.sqlite.SqliteGraphStore`.

        Reachable in principle by any importer, which is why the write
        *statements* live behind the CINV-02 lint. DESIGN.md §9: no unforced
        path exists, and every forced path fails CI or fails at boot.
        """
        return self._connection

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> PostgresGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class PostgresGraphReader(BaseGraphReader):
    """``GraphReader`` over a Postgres connection — dialect and rows only.

    Identical semantics to :class:`ccf.graph.backends.sqlite.SqliteGraphReader`
    by construction: both inherit the rendering rules and supply only their own
    dialect of the same five reads.
    """

    SELECT_LINEAGE: ClassVar[str] = """
        SELECT entry_json FROM lineage
        WHERE tenant_id = %s AND claim_kind = %s AND node_key = %s
          AND claim_id = %s
    """
    SELECT_ENTITY_HISTORY: ClassVar[str] = """
        SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM entity_claims
        WHERE tenant_id = %s AND entity_uri = %s
        ORDER BY observed_at, seq
    """
    SELECT_RELATIONSHIP_HISTORY: ClassVar[str] = """
        SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM relationship_claims
        WHERE tenant_id = %s AND relationship_key = %s
        ORDER BY observed_at, seq
    """
    SELECT_ENTITIES_AS_OF: ClassVar[str] = """
        SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM entity_claims
        WHERE tenant_id = %s
          AND observed_at <= %s
          AND (superseded_at IS NULL OR superseded_at > %s)
        ORDER BY entity_uri
    """
    SELECT_RELATIONSHIPS_AS_OF: ClassVar[str] = """
        SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM relationship_claims
        WHERE tenant_id = %s
          AND observed_at <= %s
          AND (superseded_at IS NULL OR superseded_at > %s)
        ORDER BY relationship_key
    """

    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self._connection = connection

    def _query(self, sql_text: str, params: tuple[object, ...]) -> Sequence[Row]:
        with self._connection.cursor() as cursor:
            cursor.execute(sql_text.encode(), params)
            return cursor.fetchall()
