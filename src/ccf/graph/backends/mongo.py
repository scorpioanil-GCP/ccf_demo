"""MongoDB ``GraphStore`` — the document substrate behind the ``mongo`` extra.

Whitepaper §7.3 (the Context Graph as first-class persisted state); DESIGN.md
§2A.5.2 (the D-IMPL-34 six semantics — physical layout is backend-internal)
and the Phase 15.2 D-06 ruling
(``.planning/phases/15.2-substrate-adapters-and-query-pushdown/15.2-CONTEXT.md``):
MongoDB is the phase's hardest differential target and its named risk budget
(plan 15.2-13). It is also the Homecams triangulation point — the substrate a
real CCF realization persisted its fabric on — reproduced here as *mechanism*
with every domain value factored out (CLAUDE.md §2.1).

**The pymongo driver is never a core dependency.** It is the ``mongo`` optional
extra, and the import lives *inside* :meth:`MongoGraphStore.__init__` so that
``import ccf``, and even ``import ccf.graph.backends.mongo``, succeed in an
environment without it — the ``ccf.similarity.chroma_index`` precedent, and the
``ccf.graph.backends.neo4j`` precedent one plan earlier.

**Verified driver ↔ server pairing (plan 15.2-13 execution).** The pinned
driver ``pymongo==4.17.0`` was verified against a live ``mongo:7`` container
(server 7.0.39) with a real round trip; the CI service leg runs exactly this
pairing. Re-verify before moving either side.

**Physical model (adapter-owned, D-IMPL-34).** Six collections mirror the
relational layout of the reference backends, every document carrying the
``partition`` and ``tenant_id`` scope fields:

* :data:`ENTITY_NODES` / :data:`RELATIONSHIP_NODES` — the node-identity rows,
  widening ``first_observed_at`` / ``last_observed_at`` and never deleting;
* :data:`ENTITY_CLAIMS` / :data:`RELATIONSHIP_CLAIMS` — the bitemporal claim
  chains, carrying ``claim_json`` verbatim plus write-time projections of the
  predicate-relevant fields (see ``ccf.graph._writer``);
* :data:`LINEAGE` — the L-axis entries;
* :data:`TRAVERSAL_EDGES` — **the doubled-edge traversal collection.** Every
  edge is stored as *two* documents, forward (``from`` subject, ``to``
  object) and reverse (``from`` object, ``to`` subject), because
  ``$graphLookup`` follows ``connectFromField → connectToField`` in **one
  direction only** while CCF traversal is undirected (`GQ-10` at
  docs/GRAPH_QUERY_SEMANTICS.md:201). Two directed lookups do not compose: an
  alternating-direction path (out, then in) is reachable by neither
  (15.2-RESEARCH.md Pitfall 3, re-verified against the live server at plan
  15.2-13 execution — a forward-only collection reaches one hop and stops).
  The doubling is what makes one ``$graphLookup`` express the undirected walk.

Compound identity (semantic 1 of D-IMPL-34) is enforced at the persistence
tier by a **unique index over the full identity field set** on every
collection, backed by upsert-on-identity writes inside the single writer's
buffered transactions: under INV-CH7-10 exactly one writer exists, every write
path is an upsert on the compound identity, and the unique index refuses a
duplicate the code could not construct anyway.

**Partitions are graphs.** A ``partition`` names one fabric's graph inside a
single MongoDB database, exactly as a Postgres schema does on a shared server
and a Neo4j partition does on a Community database. Two partitions are two
graphs, two :attr:`MongoGraphStore.graph_identity` values, and two
independently bootable fabrics.

**Timestamps are stored as canonical RFC3339 UTC text, never BSON dates.**
Comparison in the conformance suite happens on ``canonical_bytes`` of
contracts, and a native ``Date`` would round-trip at millisecond precision —
the cross-backend byte-drift trap (04-RESEARCH.md Pitfall 3). Canonical text
sorts lexicographically as chronologically, which is what keeps the as-of cut
pushable as plain text comparison (`GQ-24` at
docs/GRAPH_QUERY_SEMANTICS.md:482).

**Credentials.** The connection URI may carry userinfo
(``mongodb://user:password@host:27017/db``); it is handed to the driver whole
and is never logged, never embedded in a docstring, and never reproduced in
:attr:`MongoGraphStore.graph_identity`, which is built from
host/port/database/partition only (threat T-15.2-05, the T-04-24 postgres
precedent).

**Filters are documents, never text.** Nothing in this module concatenates,
interpolates or formats a query string, because MongoDB has none: a filter is
a ``dict`` built from typed :class:`~ccf.graph.protocols.GraphQuery` fields,
and every artifact-authored value travels as a *value* inside it (threat
T-15.2-01). The one place artifact-authored data could become query
*structure* is a classification attribute name used as a document field path,
and that passes :func:`attribute_field_path` — the single validation site — on
both the write and the read side.

**What this module deliberately does not contain: any way to write.** As with
every backend, the write path — the nine typed ``_GraphTxn`` operations as
buffered pymongo bulk operations — lives in ``ccf.graph._writer`` behind the
CINV-02 import restriction. A new backend adds a transaction *class* there; it
does not add write operations here.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from types import TracebackType
from typing import Any, ClassVar
from urllib.parse import urlsplit

from ccf.graph.protocols import GraphQuery
from ccf.graph.reader import BaseGraphReader, Row

__ccf_mode__ = "algorithmic"

#: The public surface is deliberately four names. The collection constants,
#: the attribute-field prefix and :func:`attribute_field_path` below are
#: module-level and importable — ``ccf.graph._writer`` needs all three — but
#: they are **not** public surface: the physical layout is backend-internal by
#: D-IMPL-34, and a deployment that coded against a collection name would be
#: coding against a decision the adapter reserves the right to change. Same
#: line the Neo4j adapter draws around ``ATTRIBUTE_PROPERTY_PREFIX``.
__all__ = [
    "DEFAULT_DATABASE",
    "DEFAULT_PARTITION",
    "MongoGraphReader",
    "MongoGraphStore",
]

#: Partition the fabric's graph lives in when the caller does not say
#: otherwise. A name, not a tuning value — the SDK ships no domain vocabulary
#: (CINV-01); mirrors ``ccf.graph.backends.postgres.DEFAULT_SCHEMA`` and
#: ``ccf.graph.backends.neo4j.DEFAULT_PARTITION``.
DEFAULT_PARTITION = "ccf"

#: Database a store attaches to when neither the URI path nor the caller names
#: one. Same posture as :data:`DEFAULT_PARTITION`: a name, never a value.
DEFAULT_DATABASE = "ccf"

#: The six collections of the adapter-owned physical model (D-IMPL-34). The
#: names are SDK-owned constants — code-authored in full, never assembled from
#: caller data — so no artifact-authored string ever names a collection.
ENTITY_NODES = "ccf_entity_nodes"
ENTITY_CLAIMS = "ccf_entity_claims"
RELATIONSHIP_NODES = "ccf_relationship_nodes"
RELATIONSHIP_CLAIMS = "ccf_relationship_claims"
LINEAGE = "ccf_lineage"
#: The doubled-edge traversal collection — see the module docstring. Named
#: here so the write path in ``ccf.graph._writer`` and the ``$graphLookup``
#: stage below cannot drift apart on the layout the directed stage requires.
TRAVERSAL_EDGES = "ccf_traversal_edges"

#: Prefix under which write-time projections of claim attributes land as
#: document fields (see ``ccf.graph._writer``). The prefix is injective over
#: attribute names and disjoint from every adapter-owned field name, so an
#: artifact-authored attribute can never collide with the physical model.
ATTRIBUTE_FIELD_PREFIX = "attr_"

#: The charset an artifact-authored attribute name must satisfy before it may
#: become a MongoDB **document field path**. See :func:`attribute_field_path`.
_ATTRIBUTE_NAME = re.compile(r"[A-Za-z0-9_-]+")

#: A filter that matches nothing, without naming a field of the physical
#: model. The document rendering of SQLite's ``0 = 1`` guard: an ``$or`` with
#: no admissible branch is not a legal MongoDB document, so the
#: never-admissible case needs a positive representation (`GQ-08` at
#: docs/GRAPH_QUERY_SEMANTICS.md:163 — a policy family declaring no class is a
#: family admitting nothing).
_MATCHES_NOTHING: dict[str, Any] = {"_id": {"$in": []}}


def attribute_field_path(attribute: str) -> str | None:
    """The ONE site where an artifact-authored attribute name becomes a field path.

    Plan 15.2-13 field-path safety (threat T-15.2-01). Classification
    attribute names are **artifact-authored data**. Everywhere else in this
    adapter such data travels as a *value* inside a filter document, where it
    is inert. Here it cannot: a projected attribute is addressed by its
    **field name**, and a MongoDB field path is structure, not a value — it
    cannot be parameterized, and a name containing ``.`` addresses a *nested*
    key rather than the literal one (silently diverging from the fallback's
    ``attributes.get(name)``), while a name beginning ``$`` is read as an
    operator or an aggregation field reference.

    So a name is admitted only when it matches ``^[A-Za-z0-9_-]+$`` — which
    excludes ``$`` and ``.`` by construction rather than by a blocklist — and
    the answer is the prefixed field path. A name outside the charset returns
    ``None``, and both callers treat that as a refusal to make it structure:

    * the **write** side (``ccf.graph._writer``) does not project the
      attribute at all. Nothing is lost — ``claim_json`` still carries the
      attribute verbatim, and the fallback reads it from there;
    * the **read** side (:meth:`MongoGraphReader._translate_query`) declines
      the whole translation, and the fallback answers the whole query
      (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583) — byte-identical under
      D-04, visible only in telemetry (`GQ-34` at
      docs/GRAPH_QUERY_SEMANTICS.md:609).

    A legal CCF claim is therefore never refused by this rule; only the
    *pushdown* of a predicate over an unsafe name is.
    """
    if _ATTRIBUTE_NAME.fullmatch(attribute) is None:
        return None
    return ATTRIBUTE_FIELD_PREFIX + attribute


def _graph_identity(uri: str, *, database: str, partition: str) -> str:
    """Name the graph a URI points at, without carrying its credentials.

    The single-writer boot check keys on this string, so it has to be stable
    and it has to distinguish two graphs — but it is also the string that ends
    up in exception messages, which is why the userinfo is dropped rather than
    merely "not usually shown" (threat T-15.2-05; the T-04-24 postgres
    precedent). Two partitions in one database are two graphs, exactly as two
    Postgres schemas are.
    """
    parts = urlsplit(uri)
    host = parts.hostname or "localhost"
    port = parts.port or 27017
    return f"mongodb://{host}:{port}/{database}#{partition}"


def _database_in(uri: str) -> str | None:
    """The database named by a connection URI's path, when it names one."""
    name = urlsplit(uri).path.lstrip("/")
    return name or None


#: Compound unique indexes over the identities of the six collections. The
#: field lists are code-authored in full — no identifier interpolation exists
#: in this module — and every one of them is the persistence-tier rendering of
#: D-IMPL-34 semantic 1 (compound identity), the ``(tenant_id, entity_uri)``
#: unique index of whitepaper §7.3 extended by the partition.
_INDEXES: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    (ENTITY_NODES, ("partition", "tenant_id", "entity_uri"), True),
    (ENTITY_CLAIMS, ("partition", "tenant_id", "entity_uri", "claim_id"), True),
    (ENTITY_CLAIMS, ("partition", "tenant_id", "observed_at"), False),
    (RELATIONSHIP_NODES, ("partition", "tenant_id", "relationship_key"), True),
    (
        RELATIONSHIP_CLAIMS,
        ("partition", "tenant_id", "relationship_key", "claim_id"),
        True,
    ),
    (RELATIONSHIP_CLAIMS, ("partition", "tenant_id", "observed_at"), False),
    (
        LINEAGE,
        (
            "partition",
            "tenant_id",
            "claim_kind",
            "node_key",
            "claim_id",
            "lineage_id",
        ),
        True,
    ),
    (
        TRAVERSAL_EDGES,
        ("partition", "tenant_id", "relationship_key", "direction"),
        True,
    ),
    # The traversal index the `$graphLookup` stage walks on: `connectToField`
    # is `from`, so every hop is a lookup on this key.
    (TRAVERSAL_EDGES, ("partition", "tenant_id", "from"), False),
)


class MongoGraphStore:
    """Connection and index owner for the MongoDB backend — extras-gated.

    Args:
        uri: MongoDB connection URI (``mongodb://…`` or ``mongodb+srv://…``),
            optionally carrying userinfo. Supplied by the deployment
            (typically from an environment variable); never committed, never
            logged, and never echoed back through :attr:`graph_identity`.
        partition: Which graph in this database this store attaches to. Two
            partitions in one database are two graphs — what lets one server
            host several fabrics, and what makes the single-writer check
            meaningful per fabric rather than per server (the Postgres
            ``schema`` argument's role, exactly).
        database: Database name. ``None`` takes the one named by the URI's
            path, falling back to :data:`DEFAULT_DATABASE`.

    As with every backend store, this is *not* a store offering both halves of
    the Protocol: it offers :attr:`reader`, and the collection surface to the
    writer module alone.

    Raises:
        ModuleNotFoundError: When the ``mongo`` extra is not installed. Raised
            here rather than at import so the module remains importable and
            the failure names the moment a deployment actually asked for
            MongoDB: install it with ``pip install "ccf[mongo]"``.
    """

    def __init__(
        self,
        *,
        uri: str,
        partition: str = DEFAULT_PARTITION,
        database: str | None = None,
    ) -> None:
        import pymongo  # noqa: PLC0415 - lazy by design; see the module docstring

        resolved = (
            database
            if database is not None
            else (_database_in(uri) or DEFAULT_DATABASE)
        )
        self._database_name = resolved
        self._partition = partition
        self._identity = _graph_identity(
            uri, database=resolved, partition=partition
        )
        self._client: Any = pymongo.MongoClient(uri)
        # Fail at construction, not at first read: a store that cannot reach
        # its server is a broken deployment (exception), never a refusal.
        self._client.admin.command("ping")
        self._db: Any = self._client[resolved]
        for name, keys, unique in _INDEXES:
            self._db[name].create_index(
                [(field, 1) for field in keys], unique=unique
            )
        self._reader = MongoGraphReader(self)

    @property
    def graph_identity(self) -> str:
        """Credential-free identity of the graph this store is attached to."""
        return self._identity

    @property
    def partition(self) -> str:
        """The partition this store's graph lives in."""
        return self._partition

    @property
    def reader(self) -> MongoGraphReader:
        """The read-only view of this graph — safe to hand to anyone."""
        return self._reader

    def collection(self, name: str) -> Any:
        """One collection of this store's database.

        Reachable in principle by any importer, which is why the write
        *operations* live behind the CINV-02 lint in ``ccf.graph._writer``.
        DESIGN.md §9: no unforced path exists, and every forced path fails CI
        or fails at boot.
        """
        return self._db[name]

    def scope(self, tenant_id: str) -> dict[str, str]:
        """The two scope fields every document of this graph carries.

        One helper rather than two literals per filter: the partition is what
        keeps a reader from answering out of another fabric's graph in the
        same database, and a filter that forgot it would still return
        plausible rows.
        """
        return {"partition": self._partition, "tenant_id": tenant_id}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> MongoGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


# --- the five acquisition reads ----------------------------------------------
#
# MongoDB's dialect is a *document*, not a statement, so the five
# ``ClassVar[str]`` slots :class:`ccf.graph.reader.BaseGraphReader` declares
# carry the **name** of each read rather than its text, and :meth:`_query`
# builds the filter document from the typed positional parameters. This is
# strictly stronger than a text statement for the T-15.2-01 surface: there is
# no query language to parse, so there is nothing a value could be mistaken
# for. The names below are matched exhaustively in :meth:`_query`.

_READ_LINEAGE = "lineage"
_READ_ENTITY_HISTORY = "entity-history"
_READ_RELATIONSHIP_HISTORY = "relationship-history"
_READ_ENTITIES_AS_OF = "entities-as-of"
_READ_RELATIONSHIPS_AS_OF = "relationships-as-of"

#: What a claim row must expose for
#: :func:`ccf.graph.reader.materialize_view` — the shared materialization
#: core's input columns, and nothing else. Projections are explicit so a
#: physical-model field can never leak into a row the core did not ask for.
#: Projections are written with booleans rather than 1/0 deliberately: they
#: are field *selections*, and a module-level table of numbers in SDK code is
#: what CINV-01 exists to refuse (CLAUDE.md §11 — mechanism, not values).
_ENTITY_CLAIM_PROJECTION: dict[str, bool] = {
    "_id": False,
    "entity_uri": True,
    "claim_id": True,
    "claim_json": True,
    "policy_bundle_version": True,
    "superseded_by": True,
    "superseded_at": True,
}

_RELATIONSHIP_CLAIM_PROJECTION: dict[str, bool] = {
    "_id": False,
    "relationship_key": True,
    "claim_id": True,
    "claim_json": True,
    "policy_bundle_version": True,
    "superseded_by": True,
    "superseded_at": True,
}


def _as_of_clauses(boundary: str) -> list[dict[str, Any]]:
    """The as-of cut as filter documents — `GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148.

    ``observed_at <= as_of AND (superseded_at IS NULL OR superseded_at >
    as_of)``, over canonical RFC3339 text whose lexicographic order *is*
    chronological order (`GQ-24` at docs/GRAPH_QUERY_SEMANTICS.md:482). This
    is INV-CH7-14 rendered at the query tier: claims the fabric had not yet
    observed are absent, and claims superseded after the boundary are still
    current. ``{"superseded_at": None}`` matches an explicit null and an
    absent field alike, which is the same set the SQL ``IS NULL`` names.
    """
    return [
        {"observed_at": {"$lte": boundary}},
        {
            "$or": [
                {"superseded_at": None},
                {"superseded_at": {"$gt": boundary}},
            ]
        },
    ]


def _validity_clauses(boundary: str) -> list[dict[str, Any]]:
    """The validity-window cut — `GQ-09` at docs/GRAPH_QUERY_SEMANTICS.md:185.

    ``valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)``
    (INV-CH7-25, cut 3 of the in-process temporal operator) over the
    write-time canonical re-renderings, so the pushed comparison is
    fixed-width text against the canonical boundary. An absent projection —
    a claim the write path could not re-render — matches neither ``$lte`` nor
    ``$gt`` (MongoDB comparison operators do not match across BSON types), so
    the predicate is fail-closed on state it cannot chronologically order,
    never over-disclosing (threats T-15.2-03/T-15.2-26).
    """
    return [
        {"valid_from_cmp": {"$lte": boundary}},
        {
            "$or": [
                {"valid_to_cmp": None},
                {"valid_to_cmp": {"$gt": boundary}},
            ]
        },
    ]


def _combine(clauses: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Fold clause documents into one filter under ``$and``.

    ``$and`` rather than a merged dict, deliberately: several clauses key on
    ``$or`` (the supersession cut, the classification cut) and a merged
    mapping would silently drop all but the last. The fold is also what makes
    the rendered filter a deterministic function of the query value.
    """
    return {"$and": list(clauses)}


class MongoGraphReader(BaseGraphReader):
    """``GraphReader`` over a MongoDB database — dialect and rows only.

    Identical semantics to every other backend reader by construction: the
    five acquisition reads below are document renderings of the same five
    reads the SQL backends express, the rows they answer are plain dicts
    satisfying :class:`ccf.graph.reader.Row`, and everything above the rows —
    lineage-at-boundary, supersession-as-of, record construction, view
    ordering — is inherited from :class:`ccf.graph.reader.BaseGraphReader` and
    the substrate-neutral materialization core, so the semantics cannot fork
    here (15.2-RESEARCH.md Pitfall 5).

    The five ``SELECT_*`` slots carry read **names**, not statement text: see
    the section comment above. ``_query(name, params)`` dispatches on the name
    and builds the filter document from the typed positional parameters.
    """

    SELECT_LINEAGE: ClassVar[str] = _READ_LINEAGE
    SELECT_ENTITY_HISTORY: ClassVar[str] = _READ_ENTITY_HISTORY
    SELECT_RELATIONSHIP_HISTORY: ClassVar[str] = _READ_RELATIONSHIP_HISTORY
    SELECT_ENTITIES_AS_OF: ClassVar[str] = _READ_ENTITIES_AS_OF
    SELECT_RELATIONSHIPS_AS_OF: ClassVar[str] = _READ_RELATIONSHIPS_AS_OF

    def __init__(self, store: MongoGraphStore) -> None:
        self._store = store

    def _query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        """Run one named acquisition read and return its rows as dicts.

        ``sql`` names the read (the five constants above); ``params`` are the
        same positional values every other backend binds. Nothing is parsed
        and nothing is formatted — the filter is a document assembled from
        these values, and the partition rides along on every one of them, so a
        reader can never answer from another fabric's graph in the same
        database.

        Raises:
            ValueError: an unknown read name reached the dispatch — an
                internal invariant violation, never a query-vocabulary
                refusal.
        """
        tenant_id = str(params[0])
        scope = self._store.scope(tenant_id)
        if sql == _READ_LINEAGE:
            rows = self._store.collection(LINEAGE).find(
                {
                    **scope,
                    "claim_kind": params[1],
                    "node_key": params[2],
                    "claim_id": params[3],
                },
                {"_id": False, "entry_json": True},
            )
            return [dict(row) for row in rows]
        if sql == _READ_ENTITY_HISTORY:
            rows = self._store.collection(ENTITY_CLAIMS).find(
                {**scope, "entity_uri": params[1]},
                _ENTITY_CLAIM_PROJECTION,
                sort=[("observed_at", 1), ("seq", 1)],
            )
            return [dict(row) for row in rows]
        if sql == _READ_RELATIONSHIP_HISTORY:
            rows = self._store.collection(RELATIONSHIP_CLAIMS).find(
                {**scope, "relationship_key": params[1]},
                _RELATIONSHIP_CLAIM_PROJECTION,
                sort=[("observed_at", 1), ("seq", 1)],
            )
            return [dict(row) for row in rows]
        if sql == _READ_ENTITIES_AS_OF:
            boundary = str(params[1])
            rows = self._store.collection(ENTITY_CLAIMS).find(
                _combine([scope, *_as_of_clauses(boundary)]),
                _ENTITY_CLAIM_PROJECTION,
                sort=[("entity_uri", 1)],
            )
            return [dict(row) for row in rows]
        if sql == _READ_RELATIONSHIPS_AS_OF:
            boundary = str(params[1])
            rows = self._store.collection(RELATIONSHIP_CLAIMS).find(
                _combine([scope, *_as_of_clauses(boundary)]),
                _RELATIONSHIP_CLAIM_PROJECTION,
                sort=[("relationship_key", 1)],
            )
            return [dict(row) for row in rows]
        raise ValueError(f"unknown MongoDB acquisition read {sql!r}")

    def _translate_query(
        self, q: GraphQuery
    ) -> tuple[Sequence[Row], Sequence[Row]] | None:
        """The aggregation-pipeline translation — installed by plan 15.2-13 Task 2."""
        del q  # Task 2 replaces this with the staged `$match` translation.
        return None
