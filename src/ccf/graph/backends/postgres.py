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
pasting it (threat T-04-23). The translated ``GraphQuery`` statements (plan
15.2-09) are *generated*, and the rule holds for them in the form that
matters: statement text is composed exclusively of code-authored fragments
plus ``%s`` placeholder repetition sized by set cardinality — every tenant
id, boundary, policy version, classification, entity URI, seed, jsonb
extraction key and depth bound travels as a bound parameter, never as text
(threat T-15.2-01). The translated as-of predicates compare canonical
RFC3339 UTC text exactly as the five fixed statements do, which is what
keeps INV-CH7-14 pushable as plain text comparison (`GQ-24` at
docs/GRAPH_QUERY_SEMANTICS.md:482).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from types import TracebackType
from typing import Any, ClassVar

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph.protocols import (
    GraphQuery,
    WriterLease,
    WriterLeaseHeld,
    WriterLeaseScope,
)
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


#: The lease statements. The key is derived SERVER-side from the session's
#: current schema — never from the DSN's host spelling, which could differ
#: (``localhost`` vs ``127.0.0.1``) for one server and so yield two keys.
#: Advisory locks are already scoped to the connected database.
_TRY_WRITER_LEASE = (
    "SELECT current_schema() AS schema_name,"
    " pg_try_advisory_lock(hashtextextended(current_schema(), 0)) AS held"
)
_RELEASE_WRITER_LEASE = (
    "SELECT pg_advisory_unlock(hashtextextended(current_schema(), 0)) AS released"
)


class PostgresWriterLease:
    """The Postgres writer lease: a session advisory lock keyed on the schema.

    SEC-013 (D-IMPL-372); whitepaper §7.3 / INV-CH7-10, CLAUDE.md §10. Scope
    ``"cross-process"``. ``pg_try_advisory_lock(hashtextextended(
    current_schema(), 0))`` on the store's own session connection:

    * **``pg_try_advisory_lock``, never ``pg_advisory_lock``** — the blocking
      form would hang a second boot instead of refusing it by name.
    * **Session-scoped, not ``_xact``** — under autocommit a transaction lock
      ends with its statement.
    * **Keyed server-side** on the schema the session resolves into, so host
      spelling in the DSN cannot produce a second key for one graph.

    Released by ``pg_advisory_unlock`` with the same key, and implicitly when
    the session ends. **Deployment caveats, disclosed rather than hidden:** a
    dropped connection loses the lease silently (this writer then fails on its
    next statement, but a competing boot may already have succeeded); a
    transaction- or statement-pooled connection (PgBouncer in those modes)
    cannot carry a session lease, so the store must connect directly or through
    a session-pooled connection; the key space is the database's shared
    single-``bigint`` advisory space.

    Args:
        connection: The store's session connection, ``search_path`` already
            set to the fabric's schema.
        schema: The schema the store was opened on, cross-checked against the
            server's ``current_schema()``.

    Raises:
        WriterLeaseHeld: another session holds the lease.
        RuntimeError: the session does not resolve into ``schema``.
    """

    def __init__(
        self, *, connection: psycopg.Connection[dict[str, Any]], schema: str
    ) -> None:
        row = connection.execute(_TRY_WRITER_LEASE).fetchone()
        if row is None:
            raise RuntimeError(
                "the Postgres lease statement returned no row (SEC-013)"
            )
        resolved = row["schema_name"]
        if resolved != schema:
            if row["held"]:
                connection.execute(_RELEASE_WRITER_LEASE)
            raise RuntimeError(
                f"the Postgres session resolves into schema {resolved!r}, not"
                f" {schema!r}; refusing to key a writer lease on it (SEC-013)"
            )
        if not row["held"]:
            raise WriterLeaseHeld(f"advisory lock on schema {schema!r} is held")
        self._connection: psycopg.Connection[dict[str, Any]] | None = connection
        self._schema = schema

    @property
    def scope(self) -> WriterLeaseScope:
        return "cross-process"

    @property
    def mechanism(self) -> str:
        return f"advisory lock on schema {self._schema!r}"

    def release(self) -> None:
        """Unlock the advisory lock. Idempotent.

        A closed or broken session has already ended, and the server released
        every session lock with it, so there is nothing left to unlock.
        """
        connection, self._connection = self._connection, None
        if connection is None or connection.closed:
            return
        try:
            connection.execute(_RELEASE_WRITER_LEASE)
        except (psycopg.OperationalError, psycopg.InterfaceError):
            return

    def __enter__(self) -> PostgresWriterLease:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


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
        self._schema = schema
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

    def writer_lease(self) -> WriterLease:
        """Acquire the cross-process writer lease (SEC-013): see :class:`PostgresWriterLease`.

        Called by the mint only, never at open: a read-only store over a live
        fabric's schema is legitimate and takes no lease.

        Raises:
            WriterLeaseHeld: another session — in any process — has the lease.
        """
        return PostgresWriterLease(connection=self._connection, schema=self._schema)

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


# --- GraphQuery translation (plan 15.2-09) -----------------------------------
#
# The Postgres half of the pushdown pair: the same statement structure as
# ccf.graph.backends.sqlite — one WITH chain (survivors / edges / walk), two
# outer SELECTs, one positional parameter tuple — in the %s dialect with
# jsonb extraction. The hook contract is all-or-nothing (`GQ-32` at
# docs/GRAPH_QUERY_SEMANTICS.md:583); both statements feed
# ccf.graph.reader.materialize_view exactly as the five fixed statements do,
# so lineage-at-boundary and supersession-as-of stay rendered in the one
# shared place (INV-CH7-14). One deliberate dialect asymmetry: the
# classification attribute name binds as a bare jsonb key (`-> 'attributes'
# ->> %s`), not a path, so no charset validation site exists here — any
# artifact-authored name is pure data, exactly as in the fallback's
# attributes.get(name).

#: A constant-false predicate: SQL has no empty IN list, and an empty set
#: admits nothing.
_FALSE = "FALSE"

#: The six answer columns, aliased from the survivors CTE.
_ENTITY_ANSWER = (
    "SELECT s.entity_uri, s.claim_id, s.claim_json, s.policy_bundle_version,\n"
    "       s.superseded_by, s.superseded_at\n"
    "FROM survivors s\n"
)

#: The six answer columns, aliased from the edges CTE.
_RELATIONSHIP_ANSWER = (
    "SELECT c.relationship_key, c.claim_id, c.claim_json,\n"
    "       c.policy_bundle_version, c.superseded_by, c.superseded_at\n"
    "FROM edges c\n"
)

#: The undirected step: whichever endpoint of the joined crossable edge is
#: not the walk row's own node (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201
#: — an edge is crossable in either direction).
_REACHED = (
    "CASE WHEN c.subject_uri = w.uri THEN c.object_uri ELSE c.subject_uri END"
)

#: The recursive term's join, ONE per direction (`GQ-10` at
#: docs/GRAPH_QUERY_SEMANTICS.md:201, semantics version 1.2.0; ledger row
#: 24.5-L-06). Under ``direction="undirected"`` an edge is crossable from
#: either endpoint; under ``direction="forward"`` only from its stored
#: ``subject_uri``. ``direction`` chooses between these two code-authored
#: constants in Python — it is never rendered into statement text (threat
#: T-24.5-12) — and ``_REACHED`` above is unchanged: under the forward join
#: its CASE simply always takes the ``object_uri`` branch.
_HOP_JOIN_UNDIRECTED = (
    "      ON (c.subject_uri = w.uri OR c.object_uri = w.uri)\n"
)
_HOP_JOIN_FORWARD = "      ON c.subject_uri = w.uri\n"


def _placeholders(count: int) -> str:
    """A generated ``%s`` list of ``count`` members — structure, never values."""
    return ", ".join(["%s"] * count)


def _in_clause(
    expression: str, values: Iterable[str]
) -> tuple[str, tuple[str, ...]]:
    """``expression IN (%s, ...)`` with sorted bound values; empty is false.

    Set members are always values, never text (threat T-15.2-01): the
    fragment carries generated placeholders only, and the members return as
    parameters. Sorting makes the rendered statement a deterministic
    function of the query value.
    """
    ordered = tuple(sorted(values))
    if not ordered:
        return _FALSE, ()
    return expression + " IN (" + _placeholders(len(ordered)) + ")", ordered


def _utc_fixed_width(expression: str) -> str:
    """Normalize a claim-JSON timestamp rendering to fixed-width UTC text.

    Claim JSON renders UTC datetimes with a ``Z`` suffix and either no
    fractional part (whole seconds) or exactly six fractional digits — two
    widths that do NOT compare chronologically against the fixed-width
    canonical boundary (``...05Z`` sorts *after* ``...05.000000Z``). This
    expression widens the whole-second form so both compare as canonical
    text (`GQ-24` at docs/GRAPH_QUERY_SEMANTICS.md:482). A rendering that
    is not ``Z``-suffixed (a claim authored with a non-UTC offset — legal
    at the contract tier) yields NULL, and NULL fails every comparison:
    the pushed predicate is fail-closed on state it cannot chronologically
    order as text, never over-disclosing (threats T-15.2-03/T-15.2-26).
    """
    return (
        "CASE WHEN right(" + expression + ", 1) = 'Z'"
        " THEN CASE WHEN position('.' in " + expression + ") > 0"
        " THEN " + expression
        + " ELSE replace(" + expression + ", 'Z', '.000000Z') END END"
    )


def _validity_clauses(
    prefix: str, json_column: str, boundary: str
) -> tuple[str, tuple[str, str]]:
    """The validity-window cut over the claim's own jsonb fields.

    `GQ-09` at docs/GRAPH_QUERY_SEMANTICS.md:185: when the temporal family
    requires validity at the boundary, a record additionally survives only
    if ``valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)``
    — cut 3 of the in-process temporal operator (INV-CH7-25), pushed as
    canonical-text comparison over the width-normalized renderings.
    """
    valid_from = "(" + json_column + "::jsonb ->> 'valid_from')"
    valid_to = "(" + json_column + "::jsonb ->> 'valid_to')"
    text = (
        # `GQ-09`'s ABSENCE LIMB (`D-IMPL-332`). `valid_from` is now genuinely
        # nullable — the fabric stopped substituting ingestion time for a
        # valid-time no source supplied — and a NULL must ADMIT rather than
        # exclude. In SQL it would otherwise exclude silently: `NULL <= x` is
        # NULL, not true, so every claim with an unknown valid-time would
        # vanish from every validity-window read.
        prefix + "AND (" + valid_from + " IS NULL OR "
        + _utc_fixed_width(valid_from) + " <= %s)\n"
        + prefix + "AND (" + valid_to + " IS NULL OR "
        + _utc_fixed_width(valid_to) + " > %s)\n"
    )
    return text, (boundary, boundary)


def _translated_statements(
    q: GraphQuery,
) -> tuple[str, str, tuple[object, ...]]:
    """Render ``q`` as the two whole-answer statements in the %s dialect.

    Returns ``(entity_sql, relationship_sql, params)`` — both statements
    share one WITH chain and one positional parameter tuple. Unlike the
    sqlite half there is no decline path: the attribute name binds as a
    bare jsonb key, so every well-formed query translates (`GQ-32` at
    docs/GRAPH_QUERY_SEMANTICS.md:583).
    """
    boundary = canonical_timestamp(q.as_of)
    policy_versions = q.permitted_policy_bundle_versions
    attribute_by_class = q.classification_attribute_by_class
    classifications = q.permitted_classifications
    # Constraint presence gates endpoint closure exactly as the fallback's
    # step 4 does: any family present, or `allowed_entities` non-None. The
    # degenerate everything-question is exempt — its answer keeps dangling
    # first-class edges (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122;
    # `GQ-21` at docs/GRAPH_QUERY_SEMANTICS.md:446).
    constrained = (
        q.allowed_entities is not None
        or policy_versions is not None
        or q.require_valid_at_boundary is not None
        or q.traverse is not None
    )
    require_validity = q.require_valid_at_boundary is True

    text: list[str] = []
    params: list[object] = []

    # survivors: the surviving entity claims. The as-of cut is INV-CH7-14
    # rendered at the query tier (`GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148)
    # over the canonical-text observed_at / superseded_at columns; the
    # remaining families narrow within it.
    # MATERIALIZED (Postgres 12+) removes planner discretion: each CTE
    # computes once per statement, so the walk's recursive term expands over
    # a computed row set rather than re-evaluating a subquery per candidate
    # row — the difference between a bounded walk and a combinatorial
    # re-scan on demo-scale graphs.
    text.append("survivors AS MATERIALIZED (\n")
    text.append(
        "    SELECT ec.entity_uri, ec.claim_id, ec.claim_json,\n"
        "           ec.policy_bundle_version, ec.superseded_by,\n"
        "           ec.superseded_at\n"
        "    FROM entity_claims ec\n"
        "    WHERE ec.tenant_id = %s\n"
        "      AND ec.observed_at <= %s\n"
        "      AND (ec.superseded_at IS NULL OR ec.superseded_at > %s)\n"
    )
    params += [q.tenant_id, boundary, boundary]
    if require_validity:
        clause, bound = _validity_clauses("      ", "ec.claim_json", boundary)
        text.append(clause)
        params += list(bound)
    if policy_versions is not None:
        # Policy admissibility, all three cuts of `GQ-08` at
        # docs/GRAPH_QUERY_SEMANTICS.md:163 (INV-CH7-26): a permitted bundle
        # version; a class with a declared classification attribute — a
        # class with none is inadmissible, so admissibility is an OR over
        # the declared classes; and a permitted value of that attribute —
        # ``->>`` answers NULL for an absent attribute, and NULL is never
        # IN a permitted set, so "carries no value" is inadmissible. The
        # attribute name is ARTIFACT-AUTHORED data and binds as a bare
        # jsonb key parameter, never statement text (threat T-15.2-01).
        assert attribute_by_class is not None  # noqa: S101 - GQ-02 whole family
        assert classifications is not None  # noqa: S101 - GQ-02 whole family
        clause, values = _in_clause("ec.policy_bundle_version", policy_versions)
        text.append("      AND " + clause + "\n")
        params += list(values)
        alternatives: list[str] = []
        if classifications:
            for entity_class in sorted(attribute_by_class):
                alternatives.append(
                    "((ec.claim_json::jsonb ->> 'entity_class') = %s"
                    " AND (ec.claim_json::jsonb -> 'attributes' ->> %s)"
                    " IN (" + _placeholders(len(classifications)) + "))"
                )
                params += [
                    entity_class,
                    attribute_by_class[entity_class],
                    *sorted(classifications),
                ]
        if alternatives:
            text.append(
                "      AND ("
                + "\n           OR ".join(alternatives)
                + ")\n"
            )
        else:
            text.append("      AND " + _FALSE + "\n")
    if q.allowed_entities is not None:
        # The uniform rule's set membership on entity selection (`GQ-15` at
        # docs/GRAPH_QUERY_SEMANTICS.md:300): every family computes within
        # the survivor set, restricted before anything else evaluates. The
        # set travels natively as generated placeholders (`GQ-30` at
        # docs/GRAPH_QUERY_SEMANTICS.md:563); a temp-table strategy is a
        # documented adapter-internal alternative for very large sets, not
        # required for conformance — the Control Plane cap (`GQ-18`)
        # governs set size upstream of this statement.
        clause, values = _in_clause("ec.entity_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
    text.append(")")

    # edges: the surviving relationship claims that may appear in the answer
    # — and, on a traverse query, the walk's whole expansion surface: the
    # relationship_claims join carries the as-of predicate (INV-CH7-14;
    # `GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148) plus the segment's
    # validity and policy predicates when present, and endpoint closure
    # below restricts crossability to edges between surviving entities.
    text.append(",\nedges AS MATERIALIZED (\n")
    text.append(
        "    SELECT rc.relationship_key, rc.claim_id, rc.claim_json,\n"
        "           rc.policy_bundle_version, rc.superseded_by,\n"
        "           rc.superseded_at, r.subject_uri, r.object_uri\n"
        "    FROM relationship_claims rc\n"
        "    JOIN relationships r\n"
        "      ON r.tenant_id = %s\n"
        "     AND r.relationship_key = rc.relationship_key\n"
        "    WHERE rc.tenant_id = %s\n"
        "      AND rc.observed_at <= %s\n"
        "      AND (rc.superseded_at IS NULL OR rc.superseded_at > %s)\n"
    )
    params += [q.tenant_id, q.tenant_id, boundary, boundary]
    if require_validity:
        clause, bound = _validity_clauses("      ", "rc.claim_json", boundary)
        text.append(clause)
        params += list(bound)
    if policy_versions is not None:
        # A relationship is admissible under the policy family iff its
        # bundle version is permitted (`GQ-08` at
        # docs/GRAPH_QUERY_SEMANTICS.md:163) — no classification cut of its
        # own; endpoint survival governs its exposure below.
        clause, values = _in_clause("rc.policy_bundle_version", policy_versions)
        text.append("      AND " + clause + "\n")
        params += list(values)
    if q.allowed_entities is not None:
        # The induced-subgraph rule (`GQ-16` at
        # docs/GRAPH_QUERY_SEMANTICS.md:316): both endpoints members of the
        # set, stated natively on the edge's own columns.
        clause, values = _in_clause("r.subject_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
        clause, values = _in_clause("r.object_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
    if q.traverse is not None:
        # Typed crossability doubles as answer membership: edges of other
        # types are absent even between reached endpoints (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201).
        clause, values = _in_clause(
            "r.relationship_type", q.traverse.relationship_types
        )
        text.append("      AND " + clause + "\n")
        params += list(values)
    if constrained:
        # Endpoint closure against the surviving universe (`GQ-16` at
        # docs/GRAPH_QUERY_SEMANTICS.md:316, INV-CH7-40): an answer view
        # never retains an edge to a node its principal may not see. The
        # degenerate everything-question skips this — a dangling
        # first-class edge is state, not a leak, in the unconstrained
        # answer (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122).
        text.append(
            "      AND EXISTS (SELECT 1 FROM survivors s\n"
            "                  WHERE s.entity_uri = r.subject_uri)\n"
            "      AND EXISTS (SELECT 1 FROM survivors s\n"
            "                  WHERE s.entity_uri = r.object_uri)\n"
        )
    text.append(")\n")

    if q.traverse is not None:
        # The bounded typed undirected walk (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201, INV-CH7-24). Walk starting
        # points are the union of seed-class selection and explicit seeds,
        # computed over survivors only (`GQ-11` at
        # docs/GRAPH_QUERY_SEMANTICS.md:221) — so starts satisfy every
        # segment predicate and, when `allowed_entities` is present, sit
        # inside the set (seed classes select within it; explicit seeds
        # intersect with it, and a URI naming nothing in scope contributes
        # no start). depth_limit=0 is the base case alone: the walk
        # starting points only, a legal bound and not an error.
        text.append(",\nwalk(uri, depth) AS (\n")
        text.append(
            "    SELECT s.entity_uri, 0\n"
            "    FROM survivors s\n"
            "    WHERE "
        )
        starts: list[str] = []
        clause, values = _in_clause(
            "(s.claim_json::jsonb ->> 'entity_class')",
            q.traverse.seed_entity_classes,
        )
        starts.append(clause)
        params += list(values)
        if q.seeds:
            clause, values = _in_clause("s.entity_uri", q.seeds)
            starts.append(clause)
            params += list(values)
        text.append("(" + " OR ".join(starts) + ")\n")
        # The recursive term: hop admissibility enforced on every hop, not
        # on the result set (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261,
        # INV-CH7-40). The expansion surface is the materialized crossable
        # set above — relationship_claims joined with the as-of predicate,
        # the segment's validity and policy predicates, the permitted
        # types, and BOTH endpoints surviving — so an edge to an excluded
        # node is not a hop the walk can take, and a path through an
        # excluded node does not exist. Prune before walking, exactly the
        # fallback's shape. The join is chosen by `direction` (1.2.0;
        # ledger row 24.5-L-06) between two constants — either endpoint
        # under "undirected", the stored subject only under "forward" —
        # a Python branch, never text (threat T-24.5-12).
        text.append(
            "  UNION\n"
            "    SELECT " + _REACHED + ",\n"
            "           w.depth + 1\n"
            "    FROM walk w\n"
            "    JOIN edges c\n"
        )
        text.append(
            _HOP_JOIN_FORWARD
            if q.traverse.direction == "forward"
            else _HOP_JOIN_UNDIRECTED
        )
        text.append("    WHERE w.depth < %s\n")
        # Depth is a bound parameter in SQL — the literal-inlining
        # exception is Cypher-only (plan 15.2-09).
        params.append(q.traverse.depth_limit)
        if q.allowed_entities is not None:
            # The uniform rule inside the recursive term (`GQ-15` at
            # docs/GRAPH_QUERY_SEMANTICS.md:300): a hop to an out-of-set
            # node must not extend the walk — the D-IMPL-87 resurrection
            # defect closed in SQL. The crossable set's endpoint predicates
            # already imply membership (survivors are restricted to the
            # set); this predicate states it on the reached node itself, so
            # the closure is explicit in the term that expands the walk.
            clause, values = _in_clause(_REACHED, q.allowed_entities)
            text.append("      AND " + clause + "\n")
            params += list(values)
        if q.traverse.admitted_entity_classes is not None:
            # Node-class admission on the REACHED node, honored natively
            # (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, semantics
            # version 1.1.0; ledger row 24.5-L-05): a hop lands only on a
            # survivor whose class is admitted. Stated inside the recursive
            # term so a path through an unadmitted node does not exist, and
            # never on the base case — starts are selected by `GQ-11` and
            # are not filtered by admission. The class list binds as
            # parameters, appended in the same order the seed-class binder
            # appends (threat T-24.5-10); an empty set renders the always-
            # false clause, so no hop is admitted and the starts answer.
            clause, values = _in_clause(
                "(a.claim_json::jsonb ->> 'entity_class')",
                q.traverse.admitted_entity_classes,
            )
            text.append(
                "      AND " + _REACHED + " IN (\n"
                "        SELECT a.entity_uri FROM survivors a\n"
                "        WHERE " + clause + ")\n"
            )
            params += list(values)
        text.append(")\n")

    prologue = "WITH RECURSIVE " if q.traverse is not None else "WITH "
    with_chain = prologue + "".join(text)

    entity_answer = _ENTITY_ANSWER
    relationship_answer = _RELATIONSHIP_ANSWER
    if q.traverse is not None:
        # The traverse answer: reached entities, and the permitted-type
        # surviving edges among them (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201).
        entity_answer += "WHERE s.entity_uri IN (SELECT uri FROM walk)\n"
        relationship_answer += (
            "WHERE c.subject_uri IN (SELECT uri FROM walk)\n"
            "  AND c.object_uri IN (SELECT uri FROM walk)\n"
        )
    entity_answer += "ORDER BY s.entity_uri"
    relationship_answer += "ORDER BY c.relationship_key"
    return (
        with_chain + entity_answer,
        with_chain + relationship_answer,
        tuple(params),
    )


class PostgresGraphReader(BaseGraphReader):
    """``GraphReader`` over a Postgres connection — dialect and rows only.

    Identical semantics to :class:`ccf.graph.backends.sqlite.SqliteGraphReader`
    by construction: both inherit the rendering rules and supply only their own
    dialect of the same five reads.

    Since plan 15.2-09 the reader also holds the %s-dialect ``GraphQuery``
    translation: :meth:`_translate_query` answers whole queries by generated
    SQL — as-of + policy + validity predicates over jsonb extraction,
    ``allowed_entities`` membership, and bounded undirected traversal via
    recursive CTE — and the CI postgres leg holds the translated answers
    byte-identical to the fallback (`GQ-31` at
    docs/GRAPH_QUERY_SEMANTICS.md:573).
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

    def _translate_query(
        self, q: GraphQuery
    ) -> tuple[Sequence[Row], Sequence[Row]] | None:
        """Answer the whole query natively (plan 15.2-09).

        The hook contract is all-or-nothing (`GQ-32` at
        docs/GRAPH_QUERY_SEMANTICS.md:583): the return is the complete
        answer's row pair — every predicate family applied, hop
        admissibility applied, ``allowed_entities`` membership applied.
        This dialect declines nothing: the classification attribute name
        binds as a bare jsonb key, so every well-formed query translates.
        ``admitted_entity_classes`` (`GQ-10` at
        docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0) is HONORED natively — a
        class predicate on the reached survivor inside the recursive walk
        term, the classes bound as parameters. ``direction`` (`GQ-10`,
        1.2.0; ledger row ``24.5-L-06``) is HONORED natively: the recursive
        term joins the crossable set from either endpoint under
        ``"undirected"`` and from the stored subject only under
        ``"forward"`` — a Python choice between :data:`_HOP_JOIN_FORWARD`
        and :data:`_HOP_JOIN_UNDIRECTED`, never a value in statement text —
        and the differential suite holds the answer to the fallback over
        ``tests/conformance/query_corpus.py::direction_cases``.
        """
        if q.allowed_entities is not None and not q.allowed_entities:
            # The empty survivor set IS the answer (`GQ-04` at
            # docs/GRAPH_QUERY_SEMANTICS.md:98): the empty view, answered
            # here without a substrate round trip. An empty answer is an
            # answer, never an error (`GQ-23` at
            # docs/GRAPH_QUERY_SEMANTICS.md:474).
            return (), ()
        entity_sql, relationship_sql, params = _translated_statements(q)
        return (
            self._query(entity_sql, params),
            self._query(relationship_sql, params),
        )
