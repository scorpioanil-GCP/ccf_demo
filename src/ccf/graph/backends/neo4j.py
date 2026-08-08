"""Neo4j ``GraphStore`` — the graph-native substrate behind the ``neo4j`` extra.

Whitepaper §7.3 (the Context Graph as first-class persisted state); DESIGN.md
§2A.5.2 (the D-IMPL-34 six semantics — physical layout is backend-internal)
and the Phase 15.2 D-06 ruling
(``.planning/phases/15.2-substrate-adapters-and-query-pushdown/15.2-CONTEXT.md``):
the Neo4j adapter is the strongest pushdown test of the read seam — a
substrate whose *own* query language answers ``GraphQuery`` traversal
natively (plan 15.2-12).

**The neo4j driver is never a core dependency.** It is the ``neo4j`` optional
extra, and the import lives *inside* :meth:`Neo4jGraphStore.__init__` so that
``import ccf``, and even ``import ccf.graph.backends.neo4j``, succeed in an
environment without it — the ``ccf.similarity.chroma_index`` precedent.
Constructing the store is the first moment the dependency is needed, and the
first moment it is demanded.

**Verified driver ↔ server pairing (research assumption A1).** The pinned
driver ``neo4j==6.2.0`` was verified against a live ``neo4j:5-community``
(server 5.26.x line) container with a real Bolt round trip at plan 15.2-12
execution: the 6.x driver speaks Bolt to the 5.x server. The CI service leg
runs exactly this pairing; re-verify before moving either side.

**Physical model (adapter-owned, D-IMPL-34).** Five node shapes and one
relationship type mirror the relational layout of the reference backends:

* ``(:CcfEntity {partition, tenant_id, entity_uri, entity_class,
  first_observed_at, last_observed_at})`` — the node-identity row;
* ``(:CcfEntityClaim { … })`` / ``(:CcfRelationshipClaim { … })`` — the
  bitemporal claim chains, carrying ``claim_json`` verbatim plus write-time
  projections of the predicate-relevant fields (see ``ccf.graph._writer``);
* ``(:CcfLineage { … })`` — the L-axis entries;
* ``(a:CcfEntity)-[:CCF_EDGE {relationship_key, relationship_type, …}]->
  (b:CcfEntity)`` — the traversable graph edge. The Cypher relationship
  *type* is the fixed SDK-owned ``CCF_EDGE``, deliberately: CCF relationship
  types are artifact-authored vocabulary, and rendering one into a Cypher
  pattern would put artifact data into query text. The CCF type travels as
  the ``relationship_type`` property and is constrained via driver
  parameters (threat T-15.2-01).
* ``(:CcfMeta {partition, key, value})`` — the insertion-order counter
  (``seq``), the graph rendering of SQLite's ``rowid`` / Postgres's
  ``BIGSERIAL``.

Compound identity (semantic 1 of D-IMPL-34) is enforced at the persistence
tier by ``MERGE`` over the full identity property set inside the single
writer's transactions — the same structural argument as the memory backend's
dict keys: under INV-CH7-10 exactly one writer exists, and every write path
is a ``MERGE`` on the compound identity, so a duplicate row is
unconstructable. Composite range indexes back the identity lookups.

**Partitions are graphs.** A ``partition`` names one fabric's graph inside a
single Neo4j database, exactly as a Postgres schema does on a shared server
(Community edition has one database; partitions are what make "a fresh graph
per boot" true on it). Two partitions are two graphs, two
``graph_identity`` values, and two independently bootable fabrics.

**Timestamps are stored as canonical RFC3339 UTC text, never Neo4j temporal
types.** Comparison in the conformance suite happens on ``canonical_bytes``
of contracts, and a native temporal type would round-trip at the substrate's
own precision — the cross-backend byte-drift trap (04-RESEARCH.md Pitfall 3).
Canonical text sorts lexicographically as chronologically, which is what
keeps the as-of cut pushable as plain text comparison (`GQ-24` at
docs/GRAPH_QUERY_SEMANTICS.md:482).

**Credentials.** The connection URI may carry userinfo
(``neo4j://user:password@host:7687``); it is parsed once, handed to the
driver as an auth pair, and never logged, never embedded in a docstring, and
never reproduced in :attr:`Neo4jGraphStore.graph_identity`, which is built
from host/port/database/partition only (threat T-15.2-05, the T-04-24
postgres precedent).

**What this module deliberately does not contain: any way to write.** As
with every backend, the write path — the nine typed ``_GraphTxn`` operations
as parameterized Cypher — lives in ``ccf.graph._writer`` behind the CINV-02
import restriction. A new backend adds a transaction *class* there; it does
not add write statements here.

Every statement is parameterized; no value is ever rendered into query text.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Any, ClassVar
from urllib.parse import urlsplit

from ccf.graph.reader import BaseGraphReader, Row

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEFAULT_PARTITION",
    "Neo4jGraphReader",
    "Neo4jGraphStore",
]

#: Partition the fabric's graph lives in when the caller does not say
#: otherwise. A name, not a tuning value — the SDK ships no domain
#: vocabulary (CINV-01); mirrors ``ccf.graph.backends.postgres.DEFAULT_SCHEMA``.
DEFAULT_PARTITION = "ccf"

#: Prefix under which write-time projections of claim attributes land as
#: claim-node properties (see ``ccf.graph._writer``). The prefix is injective
#: over attribute names and disjoint from every adapter-owned property name,
#: so an artifact-authored attribute can never collide with the physical
#: model. Read side: dynamic property access ``c[$key]`` with the prefixed
#: name passed as a driver parameter — the attribute name is data, never
#: query text (threat T-15.2-01).
ATTRIBUTE_PROPERTY_PREFIX = "attr_"

# Composite range indexes over the compound identities. DDL text is
# code-authored in full — no identifier interpolation exists in this module.
_SCHEMA = (
    """
    CREATE INDEX ccf_entity_identity IF NOT EXISTS
    FOR (e:CcfEntity) ON (e.partition, e.tenant_id, e.entity_uri)
    """,
    """
    CREATE INDEX ccf_entity_claim_identity IF NOT EXISTS
    FOR (c:CcfEntityClaim)
    ON (c.partition, c.tenant_id, c.entity_uri, c.claim_id)
    """,
    """
    CREATE INDEX ccf_relationship_claim_identity IF NOT EXISTS
    FOR (c:CcfRelationshipClaim)
    ON (c.partition, c.tenant_id, c.relationship_key, c.claim_id)
    """,
    """
    CREATE INDEX ccf_lineage_identity IF NOT EXISTS
    FOR (l:CcfLineage)
    ON (l.partition, l.tenant_id, l.claim_kind, l.node_key, l.claim_id)
    """,
    """
    CREATE INDEX ccf_edge_identity IF NOT EXISTS
    FOR ()-[r:CCF_EDGE]-()
    ON (r.partition, r.tenant_id, r.relationship_key)
    """,
    """
    CREATE INDEX ccf_meta_key IF NOT EXISTS
    FOR (m:CcfMeta) ON (m.partition, m.key)
    """,
)


def _split_credentials(uri: str) -> tuple[str, tuple[str, str] | None]:
    """Separate userinfo from a connection URI.

    The driver receives the credential pair through its ``auth`` argument
    and a URI with the userinfo removed; nothing downstream of this function
    ever sees the password again. Returns ``(clean_uri, auth)`` where
    ``auth`` is ``None`` when the URI carries no userinfo.
    """
    parts = urlsplit(uri)
    if parts.username is None and parts.password is None:
        return uri, None
    host = parts.hostname or ""
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    clean = parts._replace(netloc=netloc).geturl()
    return clean, (parts.username or "", parts.password or "")


def _graph_identity(uri: str, *, database: str, partition: str) -> str:
    """Name the graph a URI points at, without carrying its credentials.

    The single-writer boot check keys on this string, so it has to be stable
    and it has to distinguish two graphs — but it is also the string that
    ends up in exception messages, which is why the userinfo is dropped
    rather than merely "not usually shown" (threat T-15.2-05; the T-04-24
    postgres precedent). Two partitions on one database are two graphs,
    exactly as two Postgres schemas are.
    """
    parts = urlsplit(uri)
    host = parts.hostname or "localhost"
    port = parts.port or 7687
    return f"neo4j://{host}:{port}/{database}#{partition}"


class Neo4jGraphStore:
    """Connection and index owner for the Neo4j backend — extras-gated.

    Args:
        uri: Bolt connection URI (``neo4j://…`` or ``bolt://…``), optionally
            carrying userinfo. Supplied by the deployment (typically from an
            environment variable); never committed, never logged, and never
            echoed back through :attr:`graph_identity`.
        partition: Which graph on this server this store attaches to. Two
            partitions on one database are two graphs — what lets one
            Community-edition server host several fabrics, and what makes
            the single-writer check meaningful per fabric rather than per
            server (the Postgres ``schema`` argument's role, exactly).
        database: Neo4j database name. ``None`` selects the driver's default
            database (``neo4j`` on a Community server, which has only one).

    As with every backend store, this is *not* a store offering both halves
    of the Protocol: it offers :attr:`reader`, and the session surface to
    the writer module alone.

    Raises:
        ModuleNotFoundError: When the ``neo4j`` extra is not installed.
            Raised here rather than at import so the module remains
            importable and the failure names the moment a deployment
            actually asked for Neo4j: install it with
            ``pip install "ccf[neo4j]"``.
    """

    def __init__(
        self,
        *,
        uri: str,
        partition: str = DEFAULT_PARTITION,
        database: str | None = None,
    ) -> None:
        import neo4j  # noqa: PLC0415 - lazy by design; see the module docstring

        clean_uri, auth = _split_credentials(uri)
        self._database = database if database is not None else "neo4j"
        self._partition = partition
        self._identity = _graph_identity(
            clean_uri, database=self._database, partition=partition
        )
        self._driver: Any = neo4j.GraphDatabase.driver(clean_uri, auth=auth)
        # Fail at construction, not at first read: a store that cannot reach
        # its server is a broken deployment (exception), never a refusal.
        self._driver.verify_connectivity()
        with self.session() as session:
            for statement in _SCHEMA:
                session.run(statement).consume()
        self._reader = Neo4jGraphReader(self)

    @property
    def graph_identity(self) -> str:
        """Credential-free identity of the graph this store is attached to."""
        return self._identity

    @property
    def partition(self) -> str:
        """The partition this store's graph lives in."""
        return self._partition

    @property
    def reader(self) -> Neo4jGraphReader:
        """The read-only view of this graph — safe to hand to anyone."""
        return self._reader

    def session(self) -> Any:
        """One driver session against this store's database.

        Reachable in principle by any importer, which is why the write
        *statements* live behind the CINV-02 lint in ``ccf.graph._writer``.
        DESIGN.md §9: no unforced path exists, and every forced path fails
        CI or fails at boot.
        """
        return self._driver.session(database=self._database)

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> Neo4jGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class Neo4jGraphReader(BaseGraphReader):
    """``GraphReader`` over a Neo4j driver — dialect and rows only.

    Identical semantics to every other backend reader by construction: the
    five acquisition statements below are Cypher renderings of the same five
    reads the SQL backends express, the rows they answer are plain dicts
    satisfying :class:`ccf.graph.reader.Row`, and everything above the rows
    — lineage-at-boundary, supersession-as-of, record construction, view
    ordering — is inherited from :class:`ccf.graph.reader.BaseGraphReader`
    and the substrate-neutral materialization core, so the semantics cannot
    fork here (15.2-RESEARCH.md Pitfall 5). Under a declined translation the
    baseline acquisition applies tenant + as-of narrowing only and the
    fallback enforces the whole query (`GQ-33` at
    docs/GRAPH_QUERY_SEMANTICS.md:594).

    Positional parameters map onto ``$p0…$pN`` in statement order; the
    store's partition rides along as ``$partition`` on every statement, so
    a reader can never answer from another fabric's graph on the same
    server.
    """

    SELECT_LINEAGE: ClassVar[str] = """
        MATCH (l:CcfLineage {partition: $partition, tenant_id: $p0,
                             claim_kind: $p1, node_key: $p2, claim_id: $p3})
        RETURN l.entry_json AS entry_json
    """
    SELECT_ENTITY_HISTORY: ClassVar[str] = """
        MATCH (c:CcfEntityClaim {partition: $partition, tenant_id: $p0,
                                 entity_uri: $p1})
        RETURN c.entity_uri AS entity_uri, c.claim_id AS claim_id,
               c.claim_json AS claim_json,
               c.policy_bundle_version AS policy_bundle_version,
               c.superseded_by AS superseded_by,
               c.superseded_at AS superseded_at
        ORDER BY c.observed_at, c.seq
    """
    SELECT_RELATIONSHIP_HISTORY: ClassVar[str] = """
        MATCH (c:CcfRelationshipClaim {partition: $partition, tenant_id: $p0,
                                       relationship_key: $p1})
        RETURN c.relationship_key AS relationship_key, c.claim_id AS claim_id,
               c.claim_json AS claim_json,
               c.policy_bundle_version AS policy_bundle_version,
               c.superseded_by AS superseded_by,
               c.superseded_at AS superseded_at
        ORDER BY c.observed_at, c.seq
    """
    SELECT_ENTITIES_AS_OF: ClassVar[str] = """
        MATCH (c:CcfEntityClaim {partition: $partition, tenant_id: $p0})
        WHERE c.observed_at <= $p1
          AND (c.superseded_at IS NULL OR c.superseded_at > $p2)
        RETURN c.entity_uri AS entity_uri, c.claim_id AS claim_id,
               c.claim_json AS claim_json,
               c.policy_bundle_version AS policy_bundle_version,
               c.superseded_by AS superseded_by,
               c.superseded_at AS superseded_at
        ORDER BY c.entity_uri
    """
    SELECT_RELATIONSHIPS_AS_OF: ClassVar[str] = """
        MATCH (c:CcfRelationshipClaim {partition: $partition, tenant_id: $p0})
        WHERE c.observed_at <= $p1
          AND (c.superseded_at IS NULL OR c.superseded_at > $p2)
        RETURN c.relationship_key AS relationship_key, c.claim_id AS claim_id,
               c.claim_json AS claim_json,
               c.policy_bundle_version AS policy_bundle_version,
               c.superseded_by AS superseded_by,
               c.superseded_at AS superseded_at
        ORDER BY c.relationship_key
    """

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def _query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        """Run one parameterized Cypher read and return its rows as dicts.

        Positional values bind as ``$p0…$pN``; ``$partition`` is supplied
        from the store on every statement. Every value is a driver
        parameter — nothing is rendered into statement text.
        """
        bound: dict[str, object] = {
            f"p{index}": value for index, value in enumerate(params)
        }
        bound["partition"] = self._store.partition
        with self._store.session() as session:
            result = session.run(sql, bound)
            return [dict(record) for record in result]
