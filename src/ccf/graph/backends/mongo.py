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
from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Any, ClassVar
from urllib.parse import urlsplit

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph.protocols import (
    GraphQuery,
    WriterLease,
    WriterLeaseSource,
    acquire_declared_writer_lease,
)
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
        writer_lease: The deployment-declared writer lease
            (``src/ccf/graph/protocols.py::WriterLeaseSource``), acquired only
            when the composition root mints a writer, never at open, so a
            read-only store needs none. **Without one this store refuses to
            mint a writer** (``WriterLeaseRequired``; SEC-013, D-IMPL-374).

    As with every backend store, this is *not* a store offering both halves of
    the Protocol: it offers :attr:`reader`, and the collection surface to the
    writer module alone.

    Raises:
        ModuleNotFoundError: When the ``mongo`` extra is not installed. Raised
            here rather than at import so the module remains importable and
            the failure names the moment a deployment actually asked for
            MongoDB: install it with ``pip install "ccf-sdk[mongo]"``.
    """

    def __init__(
        self,
        *,
        uri: str,
        partition: str = DEFAULT_PARTITION,
        database: str | None = None,
        writer_lease: WriterLeaseSource | None = None,
    ) -> None:
        self._writer_lease = writer_lease
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

    def writer_lease(self) -> WriterLease:
        """Acquire the deployment-declared cross-process writer lease, or refuse.

        SEC-013 (D-IMPL-374 (1)); whitepaper §7.3 / INV-CH7-10. A second
        process can reach this store's graph, so the ``"process"`` disclosure
        is not a lease here: the mint (``src/ccf/graph/_writer.py::
        mint_boot_token``) acquires the lease declared at construction
        (``writer_lease=``) through
        ``src/ccf/graph/protocols.py::acquire_declared_writer_lease``, and with
        none declared — or one whose scope is not ``"cross-process"`` — the
        mint is refused by name. The lease is released with the boot token.

        Raises:
            WriterLeaseRequired: no held cross-process lease was declared.
            WriterLeaseHeld: another holder, in any process, has the lease.
        """
        return acquire_declared_writer_lease(
            self._writer_lease, substrate='mongo', graph_identity=self._identity
        )

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

#: The translated answers carry two write-time projections beyond the
#: materialization core's input columns: the entity class the walk's
#: start selection reads (`GQ-11` at docs/GRAPH_QUERY_SEMANTICS.md:221) and
#: the edge endpoints the induced-subgraph and closure rules read (`GQ-16` at
#: docs/GRAPH_QUERY_SEMANTICS.md:316). The core ignores what it was not asked
#: for, so the extra fields cost nothing in canonical bytes.
_SURVIVOR_PROJECTION: dict[str, bool] = {
    **_ENTITY_CLAIM_PROJECTION,
    "entity_class": True,
}

_CROSSABLE_PROJECTION: dict[str, bool] = {
    **_RELATIONSHIP_CLAIM_PROJECTION,
    "subject_uri": True,
    "object_uri": True,
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
        # `GQ-09`'s ABSENCE LIMB (`D-IMPL-332`): the write path omits the
        # field when no valid-time was supplied, and a missing field must
        # admit. `$lte` alone does not match a missing field.
        {"$or": [
            {"valid_from_cmp": {"$exists": False}},
            {"valid_from_cmp": {"$lte": boundary}},
        ]},
        {
            "$or": [
                {"valid_to_cmp": None},
                {"valid_to_cmp": {"$gt": boundary}},
            ]
        },
    ]


def _classification_clause(q: GraphQuery) -> dict[str, Any] | None:
    """`GQ-08`'s cuts 2 and 3 as one ``$or`` over the declared classes.

    `GQ-08` at docs/GRAPH_QUERY_SEMANTICS.md:163 (INV-CH7-26): an entity is
    admissible only if its class has a declared classification attribute and
    the value of that attribute is permitted. Both cuts fall out of one
    ``$or``: a class with no declared attribute contributes no branch and is
    therefore inadmissible, and an entity carrying no value for its class's
    attribute has no field to match — an absent field is never ``$in`` a set
    of strings, which is exactly what the fallback's
    ``attributes.get(name) in classifications`` computes.

    Returns ``None`` when a declared attribute name cannot safely become a
    document field path (:func:`attribute_field_path`), which declines the
    whole translation to the fallback (`GQ-32` at
    docs/GRAPH_QUERY_SEMANTICS.md:583).

    Callable only when the policy family is present; the contract guarantees a
    present family carries all of its fields (`GQ-02` at
    docs/GRAPH_QUERY_SEMANTICS.md:64), which the assertions render as type
    narrowing rather than runtime re-litigation.
    """
    attribute_by_class = q.classification_attribute_by_class
    classifications = q.permitted_classifications
    assert attribute_by_class is not None  # noqa: S101 - GQ-02 whole family
    assert classifications is not None  # noqa: S101 - GQ-02 whole family
    branches: list[dict[str, Any]] = []
    if classifications:
        permitted = sorted(classifications)
        for entity_class in sorted(attribute_by_class):
            path = attribute_field_path(attribute_by_class[entity_class])
            if path is None:
                return None
            branches.append(
                {"entity_class": entity_class, path: {"$in": permitted}}
            )
    return {"$or": branches} if branches else _MATCHES_NOTHING


def _translated_filters(
    q: GraphQuery, *, scope: Mapping[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool] | None:
    """Render ``q`` as the two ``$match`` clause lists, or decline.

    Returns ``(entity_clauses, edge_clauses, constrained)`` — the survivor
    filter, the crossable-edge filter, and whether endpoint closure applies —
    or ``None`` when a classification attribute name falls outside the safe
    field-path charset, in which case the fallback answers (`GQ-32` at
    docs/GRAPH_QUERY_SEMANTICS.md:583; D-04).

    Every clause is a document assembled from typed contract fields, and every
    set member travels as a *value* inside one (`GQ-30` at
    docs/GRAPH_QUERY_SEMANTICS.md:563): the aggregation-pipeline ``$in`` the
    semantics name as a conformant rendering of ``allowed_entities``. Sorting
    the sets makes the rendered filter a deterministic function of the query
    value.
    """
    boundary = canonical_timestamp(q.as_of)
    policy_versions = q.permitted_policy_bundle_versions
    entity_clauses: list[dict[str, Any]] = [
        dict(scope),
        *_as_of_clauses(boundary),
    ]
    edge_clauses: list[dict[str, Any]] = [dict(scope), *_as_of_clauses(boundary)]
    if q.require_valid_at_boundary is True:
        entity_clauses += _validity_clauses(boundary)
        edge_clauses += _validity_clauses(boundary)
    if policy_versions is not None:
        classification = _classification_clause(q)
        if classification is None:
            return None
        permitted = {"policy_bundle_version": {"$in": sorted(policy_versions)}}
        entity_clauses.append(permitted)
        entity_clauses.append(classification)
        # A relationship is admissible under the policy family iff its bundle
        # version is permitted (`GQ-08` at
        # docs/GRAPH_QUERY_SEMANTICS.md:163) — no classification cut of its
        # own; endpoint survival governs its exposure.
        edge_clauses.append(permitted)
    if q.allowed_entities is not None:
        # The uniform rule's set membership on entity selection (`GQ-15` at
        # docs/GRAPH_QUERY_SEMANTICS.md:300): every family computes within the
        # set, restricted before anything else evaluates — and the
        # induced-subgraph rule on edge selection (`GQ-16` at
        # docs/GRAPH_QUERY_SEMANTICS.md:316): both endpoints in the set.
        allowed = sorted(q.allowed_entities)
        entity_clauses.append({"entity_uri": {"$in": allowed}})
        edge_clauses.append({"subject_uri": {"$in": allowed}})
        edge_clauses.append({"object_uri": {"$in": allowed}})
    if q.traverse is not None:
        # Typed crossability doubles as answer membership: edges of other
        # types are absent even between reached endpoints (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201).
        edge_clauses.append(
            {"relationship_type": {"$in": sorted(q.traverse.relationship_types)}}
        )
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
    return entity_clauses, edge_clauses, constrained


def _closure_clauses(
    entity_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Endpoint closure against the materialized survivors.

    `GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316 (INV-CH7-40): an answer view
    never retains an edge to a node its principal may not see. Stated on the
    surviving URIs rather than as a sub-query, because the survivor set is
    already in hand — and because the same list is what the walk expands over,
    so the two can never disagree.
    """
    survivors = sorted({row["entity_uri"] for row in entity_rows})
    return [
        {"subject_uri": {"$in": survivors}},
        {"object_uri": {"$in": survivors}},
    ]


#: Field the ``$graphLookup`` stage writes its reached traversal documents
#: into, and the ONE aggregation *field reference* this module contains (the
#: walk's ``startWith``). Both are SDK-owned constants, code-authored in full:
#: no artifact-authored string ever becomes a pipeline field reference, which
#: is the aggregation-stage half of the field-path rule
#: :func:`attribute_field_path` states for ``$match`` (threat T-15.2-01).
_REACHED = "reached"
_START_FROM = "$entity_uri"


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
        """Answer the whole query natively in the aggregation dialect.

        The hook contract is all-or-nothing (`GQ-32` at
        docs/GRAPH_QUERY_SEMANTICS.md:583): the return is the complete
        answer's row pair — every predicate family applied, hop
        admissibility applied, ``allowed_entities`` membership applied.

        Three reads answer it. Two are filter documents over the claim
        collections; the third is the ``$graphLookup`` walk (stage 2, promoted
        in Task 3 after the corpus proved parity — see :meth:`_walk`).

        1. **survivors** — the surviving entity claims: the as-of cut
           (`GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148, INV-CH7-14) as
           canonical-text comparison, the validity window (`GQ-09` at
           docs/GRAPH_QUERY_SEMANTICS.md:185) over the write-time
           re-renderings, policy admissibility (`GQ-08` at
           docs/GRAPH_QUERY_SEMANTICS.md:163) as a bundle-version ``$in``
           plus an ``$or`` over the declared classes, and the uniform rule's
           set membership (`GQ-15` at docs/GRAPH_QUERY_SEMANTICS.md:300) as
           an ``entity_uri`` ``$in`` — the aggregation-pipeline ``$in`` the
           semantics name as one of the conformant renderings (`GQ-30` at
           docs/GRAPH_QUERY_SEMANTICS.md:563);
        2. **edges** — the surviving relationship claims that may appear in
           the answer: the same temporal cuts, the bundle-version cut, the
           induced subgraph under ``allowed_entities`` (`GQ-16` at
           docs/GRAPH_QUERY_SEMANTICS.md:316 — both endpoints in the set),
           the permitted types when a traverse family is present, and
           endpoint closure against the materialized survivors on every
           constrained answer;
        3. **walk** (traverse only, ``depth_limit >= 1``) — the bounded typed
           undirected expansion (`GQ-10` at
           docs/GRAPH_QUERY_SEMANTICS.md:201, INV-CH7-24) as one
           ``$graphLookup`` over the doubled-edge collection, with hop
           admissibility and ``allowed_entities`` membership carried in
           ``restrictSearchWithMatch`` (`GQ-13` at
           docs/GRAPH_QUERY_SEMANTICS.md:261; `GQ-15` at
           docs/GRAPH_QUERY_SEMANTICS.md:300). Walk starting points are
           computed within survivors (`GQ-11` at
           docs/GRAPH_QUERY_SEMANTICS.md:221) — seed classes select within
           the surviving universe, explicit seeds intersect with it — and the
           reached set filters both row sets, mirroring the SQL adapters'
           outer walk-membership SELECTs and the Cypher adapter's shape.

        Two shapes short-circuit without a round trip: the empty
        ``allowed_entities`` set IS the empty answer (`GQ-04` at
        docs/GRAPH_QUERY_SEMANTICS.md:98), and a classification attribute
        name that cannot safely become a document field path declines to the
        fallback (:func:`attribute_field_path`) — still answered, per D-04.

        Every filter is a ``dict`` built from typed contract fields. No value
        is ever concatenated into anything, because there is nothing to
        concatenate it into (threat T-15.2-01).

        ``admitted_entity_classes`` (`GQ-10` at
        docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0) is DECLINED: a walk
        carrying node-class admission returns ``None`` and the fallback
        answers, byte-identical by construction (D-04; `GQ-32` constrains
        only a non-``None`` return). Declined rather than narrowed because
        the ``restrictSearchWithMatch`` survivor clause has not been measured
        against the live server with a start-exempt admission set; a decline
        is conformant today and native admission is a promotion the
        differential suite can earn later (`GQ-34`). ``direction`` other
        than ``"undirected"`` (`GQ-10`, 1.2.0; ledger row ``24.5-L-06``) is
        DECLINED the same way (`GQ-32`): ``TRAVERSAL_EDGES`` is written
        doubled — one document per orientation, each carrying a
        ``direction`` field — and restricting ``$graphLookup`` to the
        forward documents has not been measured against the live server
        (24.5-RESEARCH.md assumption A1), so the fallback answers,
        byte-identical, and native direction is a `GQ-34` promotion to earn.
        """
        if q.allowed_entities is not None and not q.allowed_entities:
            # The empty survivor set IS the answer (`GQ-04`): the empty view,
            # answered without a substrate round trip. An empty answer is an
            # answer, never an error (`GQ-23` at
            # docs/GRAPH_QUERY_SEMANTICS.md:474).
            return (), ()
        if q.traverse is not None and q.traverse.direction != "undirected":
            # Decline → the fallback answers (D-04; ledger row 24.5-L-06). A
            # pure function of the query value, before any translation: a
            # pushdown that ignored `direction` would walk undirected while
            # the oracle walks directed, a divergence nothing would observe.
            return None
        if (
            q.traverse is not None
            and q.traverse.admitted_entity_classes is not None
        ):
            # Decline → the fallback answers (D-04). A pure function of the
            # query value, before any round trip — see the docstring.
            return None
        scope = self._store.scope(q.tenant_id)
        filters = _translated_filters(q, scope=scope)
        if filters is None:
            return None
        entity_clauses, edge_clauses, constrained = filters
        entity_rows = self._survivors(entity_clauses)
        if constrained:
            edge_clauses += _closure_clauses(entity_rows)
        relationship_rows = self._crossable(edge_clauses)
        if q.traverse is None:
            return entity_rows, relationship_rows
        # Walk-start selection within survivors (`GQ-11` at
        # docs/GRAPH_QUERY_SEMANTICS.md:221): seed classes select within the
        # surviving universe; explicit seeds intersect with it — a URI naming
        # nothing in scope contributes no start, which is not an error.
        survivors = {row["entity_uri"] for row in entity_rows}
        starts = {
            row["entity_uri"]
            for row in entity_rows
            if row["entity_class"] in q.traverse.seed_entity_classes
        }
        if q.seeds is not None:
            starts |= set(q.seeds) & survivors
        # **Pitfall-3 correction 2 — explicit seed re-inclusion.**
        # `$graphLookup` excludes the starting document from its `as` array
        # while CCF includes the walk starting points (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201), so the reached set is seeded
        # with the starts before the stage runs — which is also what makes
        # `depth_limit=0` (seeds only) expressible at all.
        reached = set(starts)
        if starts and q.traverse.depth_limit >= 1:
            # **Pitfall-3 correction 3 — depth_limit=0 skips the stage.**
            # `maxDepth` has no value expressing "no hops": `maxDepth: 0` is
            # already one lookup. A zero bound is a legal bound, not an error.
            reached |= self._walk(
                scope=scope,
                starts=sorted(starts),
                crossable=sorted(
                    {row["relationship_key"] for row in relationship_rows}
                ),
                survivors=sorted(survivors),
                depth_limit=q.traverse.depth_limit,
            )
        # The reached set filters both row sets — the aggregation analogue of
        # the SQL adapters' `IN (SELECT uri FROM walk)` outer SELECTs; the
        # walk itself ran in the engine.
        entity_rows = [
            row for row in entity_rows if row["entity_uri"] in reached
        ]
        relationship_rows = [
            row
            for row in relationship_rows
            if row["subject_uri"] in reached and row["object_uri"] in reached
        ]
        return entity_rows, relationship_rows

    # -- the three pushed reads the translation is built from -----------------

    def _walk(
        self,
        *,
        scope: Mapping[str, str],
        starts: list[str],
        crossable: list[str],
        survivors: list[str],
        depth_limit: int,
    ) -> set[str]:
        """The bounded typed undirected expansion, run in the engine.

        Stage 2 of the staged adapter (plan 15.2-13 Task 3), promoted only
        after the differential corpus proved byte-identity — `GQ-34` at
        docs/GRAPH_QUERY_SEMANTICS.md:609 makes the promotion an earned
        optimization, never a conformance requirement.

        Answers the set of entity URIs reachable within ``depth_limit`` hops
        of any start. Three of the four `$graphLookup` mismatch corrections
        (15.2-RESEARCH.md Pitfall 3) land in the caller
        (:meth:`_translate_query` — seed re-inclusion and the depth-0
        stage-skip) and in the **doubled-edge collection** the write path
        maintains (the stage is directed, CCF traversal is undirected, and two
        directed lookups do not compose). The fourth lands here:

        * **the ``maxDepth`` offset** — ``depthField`` starts at 0 for the
          first lookup, so CCF hop *h* is ``depthField`` *h−1* and a CCF
          ``depth_limit`` of N is ``maxDepth: N-1``. Verified against the live
          server at plan 15.2-13 execution: ``maxDepth: 0`` reaches exactly
          the one-hop neighbours and no further.

        Hop admissibility (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261,
        INV-CH7-40) and the uniform rule (`GQ-15` at
        docs/GRAPH_QUERY_SEMANTICS.md:300) ride
        ``restrictSearchWithMatch``, which filters traversal documents
        *during* the walk rather than after it — the distinction that keeps a
        path through an excluded node from existing rather than merely being
        pruned from the result (threats T-15.2-03 / T-15.2-26). Two clauses
        carry it:

        * ``relationship_key`` ∈ the **crossable** set — the edges the
          segment's own ``$match`` already admitted under the permitted types,
          the temporal cuts, the policy family, ``allowed_entities`` on both
          endpoints, and endpoint closure. Stating hop admissibility as
          membership in that already-computed set rather than re-deriving the
          predicates on traversal documents is deliberate: a re-derivation is
          a second place for the semantics to live, and the two would
          eventually disagree (the prune-before-walk shape the Postgres
          MATERIALIZED CTE and the Cypher ``all(…)`` path predicate both use);
        * ``to`` ∈ the **survivor** set — the uniform rule stated explicitly
          on the node a hop would extend the walk to. Redundant by
          construction (a crossable edge has both endpoints surviving) and
          explicit by the Postgres/Neo4j precedent: the closure belongs in the
          term that expands the walk, where a reader can see it.

        Assumption A3 (15.2-RESEARCH.md:953) was verified against the live
        ``mongo:7`` container before promotion: ``restrictSearchWithMatch``
        accepts every plain-match predicate shape the hop filter needs —
        scope equality, ``$in``, ``$lte`` on canonical text, and the
        supersession ``$or`` — with no ``$expr`` required.

        Operational note: the stage holds its reached documents in memory per
        start (100 MB stage bound). Survivor-set size is the Control Plane's
        cap to set (`GQ-18` at docs/GRAPH_QUERY_SEMANTICS.md:342), never this
        module's.
        """
        if not crossable:
            # No admissible edge exists, so no hop does either. Answered
            # without a round trip; the starts are already in `reached`.
            return set()
        pipeline: list[dict[str, Any]] = [
            {"$match": {**scope, "entity_uri": {"$in": starts}}},
            {
                "$graphLookup": {
                    "from": TRAVERSAL_EDGES,
                    "startWith": _START_FROM,
                    "connectFromField": "to",
                    "connectToField": "from",
                    "maxDepth": depth_limit - 1,
                    "restrictSearchWithMatch": {
                        **scope,
                        "relationship_key": {"$in": crossable},
                        "to": {"$in": survivors},
                    },
                    "as": _REACHED,
                }
            },
            {"$project": {"_id": False, _REACHED: True}},
        ]
        return {
            edge["to"]
            for document in self._store.collection(ENTITY_NODES).aggregate(
                pipeline
            )
            for edge in document[_REACHED]
        }

    def _survivors(
        self, clauses: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """The surviving entity claims under the segment's record predicates."""
        return [
            dict(row)
            for row in self._store.collection(ENTITY_CLAIMS).find(
                _combine(clauses),
                _SURVIVOR_PROJECTION,
                sort=[("entity_uri", 1)],
            )
        ]

    def _crossable(
        self, clauses: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """The surviving relationship claims that may appear in the answer.

        On a traverse query this is also the walk's whole expansion surface:
        permitted types, the induced subgraph under ``allowed_entities``, and
        both endpoints surviving — so an edge to an excluded node is not a hop
        the walk can take (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261).
        """
        return [
            dict(row)
            for row in self._store.collection(RELATIONSHIP_CLAIMS).find(
                _combine(clauses),
                _CROSSABLE_PROJECTION,
                sort=[("relationship_key", 1)],
            )
        ]
