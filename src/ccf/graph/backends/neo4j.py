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

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph.protocols import (
    GraphQuery,
    ProcessScopedWriterLease,
    WriterLease,
)
from ccf.graph.reader import BaseGraphReader, Row

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEFAULT_PARTITION",
    "MAX_DEPTH_CEILING",
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
    def max_traversal_depth(self) -> int:
        """The deepest traversal this adapter translates natively — the Cypher injection bound.

        :class:`~ccf.graph.protocols.TraversalDepthCapability`
        (``D-IMPL-253`` Q21), satisfied structurally: the value is this
        module's own :data:`MAX_DEPTH_CEILING`, which bounds the one literal
        the adapter injects into query text. Read off the store rather than
        authored anywhere, so a layer that has a governed response can refuse
        an over-ceiling depth **by name** without any product code carrying the
        number (CINV-01). Nothing about this seam's own behavior changes: an
        over-ceiling depth here still declines the native translation and is
        answered by the memory-bounded fallback.
        """
        return MAX_DEPTH_CEILING

    @property
    def capability_identity(self) -> str:
        """The identity a technical bound from this store is resolved by.

        :attr:`graph_identity` itself — credential-free, and already the
        string this fabric identifies this graph by — rather than a second
        name that could drift from it.
        """
        return self.graph_identity

    @property
    def partition(self) -> str:
        """The partition this store's graph lives in."""
        return self._partition

    def writer_lease(self) -> WriterLease:
        """Declare ``"process"`` writer-lease scope (SEC-013, D-IMPL-372).

        A **disclosure, not enforcement**: acquiring it does nothing, and the
        only exclusion is the composition root's in-process live-writer table
        (``src/ccf/graph/_writer.py::mint_boot_token``). The single-writer
        invariant (INV-CH7-10) is NOT enforced across processes on this
        substrate. **SEC-013 remains OPEN for this substrate.** A native cross-process lease
        (a unique lock node) is an executor proposal, unapproved (SEC-013-P1).
        """
        return ProcessScopedWriterLease(substrate="neo4j")

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


# --- GraphQuery translation (plan 15.2-12) -----------------------------------
#
# The Cypher half of the pushdown story: three statements — survivors, edges,
# walk — run inside one read transaction, each composed exclusively of
# code-authored fragments with every value travelling as a named driver
# parameter. The hook contract is all-or-nothing (`GQ-32` at
# docs/GRAPH_QUERY_SEMANTICS.md:583); the surviving rows feed
# ccf.graph.reader.materialize_view exactly as the five fixed statements do,
# so lineage-at-boundary and supersession-as-of stay rendered in the one
# shared place (INV-CH7-14). Artifact-authored identifiers — relationship
# type names, classification attribute keys — bind as parameters, never as
# statement text: the type constraint uses the parameterized
# `r.relationship_type IN $types` property form rather than a Cypher type
# pattern, and attribute lookup uses dynamic property access `c[$key]` over
# the write-time projections (threat T-15.2-01).

#: Mechanism safety bound on the ONE value this adapter inlines into query
#: text: the validated traversal-depth literal (Cypher variable-length
#: bounds cannot be parameters — research assumption A2, re-verified against
#: the live server at execution: both `-[*0..$depth]-` and a quantified
#: `{0,$depth}` are rejected with a syntax error; only literal integers
#: parse). The contrast with the Control Plane's thresholds is deliberate
#: and worth stating: the admission payload ceiling is Control Plane
#: configuration because it is deployment-tunable policy; this constant
#: bounds injected Cypher text and is not — it is a property of the
#: adapter's injection surface, not of any domain (CINV-01). A
#: ``depth_limit`` above the ceiling is still answered: the translation
#: declines and the memory-bounded fallback answers (D-04 — there is no
#: "I can't"; `GQ-29` at docs/GRAPH_QUERY_SEMANTICS.md:554). The ceiling
#: bounds Cypher text, never the query vocabulary.
MAX_DEPTH_CEILING = 100

_SURVIVORS_MATCH = (
    "MATCH (c:CcfEntityClaim {partition: $partition, tenant_id: $tenant})\n"
    "WHERE c.observed_at <= $boundary\n"
    "  AND (c.superseded_at IS NULL OR c.superseded_at > $boundary)\n"
)

#: The validity-window cut (`GQ-09` at docs/GRAPH_QUERY_SEMANTICS.md:185,
#: INV-CH7-25) over the write-time canonical re-renderings, so the pushed
#: comparison is fixed-width text against the canonical boundary (`GQ-24`
#: at docs/GRAPH_QUERY_SEMANTICS.md:482). An absent projection compares
#: NULL, and NULL fails every comparison — fail-closed, never
#: over-disclosing (threats T-15.2-03/T-15.2-26).
_ENTITY_VALIDITY = (
    # `GQ-09`'s ABSENCE LIMB (`D-IMPL-332`): the write path omits the
    # property entirely when the source supplied no valid-time, and a missing
    # property must admit rather than exclude.
    "  AND (c.valid_from_cmp IS NULL OR c.valid_from_cmp <= $boundary)\n"
    "  AND (c.valid_to_cmp IS NULL OR c.valid_to_cmp > $boundary)\n"
)

#: Policy admissibility, all three cuts of `GQ-08` at
#: docs/GRAPH_QUERY_SEMANTICS.md:163 (INV-CH7-26): a permitted bundle
#: version; a class with a declared classification attribute (a class with
#: none is inadmissible — `any` over the declared classes); and a permitted
#: value of that attribute. ``$attribute_by_class`` maps entity classes to
#: *prefixed property keys* computed in Python, read back via dynamic
#: property access — an absent property answers NULL, NULL is never IN a
#: permitted set, so "carries no value" is inadmissible exactly as the
#: fallback computes it. The attribute name is ARTIFACT-AUTHORED data and
#: binds as map-parameter content, never statement text (threat T-15.2-01).
_ENTITY_POLICY = (
    "  AND c.policy_bundle_version IN $policy_versions\n"
    "  AND any(ec IN keys($attribute_by_class)\n"
    "          WHERE c.entity_class = ec\n"
    "            AND c[$attribute_by_class[ec]] IN $classifications)\n"
)

#: The uniform rule's set membership on entity selection (`GQ-15` at
#: docs/GRAPH_QUERY_SEMANTICS.md:300): every family computes within the
#: set, restricted before anything else evaluates. The set travels as a
#: driver list parameter (`GQ-30` at docs/GRAPH_QUERY_SEMANTICS.md:563) —
#: no member is ever rendered into query text.
_ENTITY_ALLOWED = "  AND c.entity_uri IN $allowed\n"

_SURVIVORS_RETURN = (
    "RETURN c.entity_uri AS entity_uri, c.claim_id AS claim_id,\n"
    "       c.claim_json AS claim_json,\n"
    "       c.policy_bundle_version AS policy_bundle_version,\n"
    "       c.superseded_by AS superseded_by,\n"
    "       c.superseded_at AS superseded_at,\n"
    "       c.entity_class AS entity_class\n"
    "ORDER BY c.entity_uri"
)

_EDGES_MATCH = (
    "MATCH (rc:CcfRelationshipClaim {partition: $partition,"
    " tenant_id: $tenant})\n"
    "WHERE rc.observed_at <= $boundary\n"
    "  AND (rc.superseded_at IS NULL OR rc.superseded_at > $boundary)\n"
)

_EDGE_VALIDITY = (
    "  AND (rc.valid_from_cmp IS NULL OR rc.valid_from_cmp <= $boundary)\n"
    "  AND (rc.valid_to_cmp IS NULL OR rc.valid_to_cmp > $boundary)\n"
)

#: A relationship is admissible under the policy family iff its bundle
#: version is permitted (`GQ-08`) — no classification cut of its own;
#: endpoint survival governs its exposure below.
_EDGE_POLICY = "  AND rc.policy_bundle_version IN $policy_versions\n"

#: The induced-subgraph rule (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316):
#: both endpoints members of the allowed set, stated natively on the claim's
#: own projected endpoint columns.
_EDGE_ALLOWED = (
    "  AND rc.subject_uri IN $allowed\n"
    "  AND rc.object_uri IN $allowed\n"
)

#: Typed crossability doubles as answer membership: edges of other types
#: are absent even between reached endpoints (`GQ-10` at
#: docs/GRAPH_QUERY_SEMANTICS.md:201). The type list is artifact-authored —
#: it travels as a parameter against the projected property, never as a
#: Cypher relationship-type pattern.
_EDGE_TYPES = "  AND rc.relationship_type IN $types\n"

#: Endpoint closure against the surviving universe (`GQ-16`, INV-CH7-40):
#: an answer view never retains an edge to a node its principal may not
#: see. The degenerate everything-question skips this — a dangling
#: first-class edge is state, not a leak, in the unconstrained answer
#: (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122).
_EDGE_CLOSURE = (
    "  AND rc.subject_uri IN $survivors\n"
    "  AND rc.object_uri IN $survivors\n"
)

_EDGES_RETURN = (
    "RETURN rc.relationship_key AS relationship_key,\n"
    "       rc.claim_id AS claim_id, rc.claim_json AS claim_json,\n"
    "       rc.policy_bundle_version AS policy_bundle_version,\n"
    "       rc.superseded_by AS superseded_by,\n"
    "       rc.superseded_at AS superseded_at,\n"
    "       rc.subject_uri AS subject_uri, rc.object_uri AS object_uri\n"
    "ORDER BY rc.relationship_key"
)

_WALK_MATCH_PREFIX = (
    "MATCH p = (seed:CcfEntity {partition: $partition, tenant_id: $tenant})"
)
_WALK_MATCH_SUFFIX = "(x:CcfEntity)\n"

#: Hop admissibility as a path predicate (`GQ-13` at
#: docs/GRAPH_QUERY_SEMANTICS.md:261, INV-CH7-40): every node on every path
#: must be a member of the materialized survivor set — the entities that
#: passed the segment's as-of, validity, policy, and set-membership cuts —
#: so a path through an excluded node does not exist. Prune before walking,
#: exactly the fallback's shape (threats T-15.2-03/T-15.2-26).
_WALK_NODES_ALL = (
    "WHERE seed.entity_uri IN $starts\n"
    "  AND all(n IN nodes(p) WHERE n.partition = $partition\n"
    "          AND n.tenant_id = $tenant\n"
    "          AND n.entity_uri IN $survivors"
)

#: The uniform rule stated explicitly inside the path predicate (`GQ-15`):
#: the survivor list already implies membership (survivors are restricted
#: to the set before the walk), but the closure is explicit in the term
#: that expands the walk — the D-IMPL-87 resurrection defect closed in the
#: Cypher itself, with the allowed set as a driver list parameter.
_WALK_NODES_ALLOWED = " AND n.entity_uri IN $allowed"

#: Crossability as a path predicate: only the materialized crossable edges
#: — surviving, permitted-type, endpoint-closed, in-set — extend a path,
#: and the artifact-authored type list rides as ``$types`` (`GQ-10`;
#: threat T-15.2-01).
_WALK_EDGES_ALL = (
    ")\n"
    "  AND all(r IN relationships(p) WHERE r.partition = $partition\n"
    "          AND r.tenant_id = $tenant\n"
    "          AND r.relationship_key IN $crossable\n"
    "          AND r.relationship_type IN $types)\n"
)

_WALK_RETURN = "RETURN DISTINCT x.entity_uri AS entity_uri"

#: Node-class admission (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0):
#: every node of the path must be in ``$admissible`` — the survivors of an
#: admitted class PLUS the walk starts, computed in Python before the walk,
#: because ``nodes(p)`` includes the seed and starts are never filtered.
#: Declared AFTER ``_WALK_RETURN`` so the line-anchored citations of
#: ``_WALK_EDGES_ALL`` elsewhere in the tree keep resolving; it is appended
#: to the walk text between ``_WALK_NODES_ALLOWED`` and ``_WALK_EDGES_ALL``.
_WALK_NODES_ADMITTED = " AND n.entity_uri IN $admissible"

#: The reach pattern's tail — the walk's direction (`GQ-10` at
#: docs/GRAPH_QUERY_SEMANTICS.md:201, semantics version 1.2.0; ledger row
#: 24.5-L-06). Relationships are directed at write — ``neo4j_write.py``
#: merges ``(a)-[e:CCF_EDGE …]->(b)`` from the stored subject to the stored
#: object — so the forward walk is the undirected pattern with its arrow.
#: ``direction`` chooses between these two constants in Python and is never
#: rendered into query text (threat T-24.5-12). Declared after
#: ``_WALK_NODES_ADMITTED`` for the same line-anchor reason it gives.
_REACH_TAIL_UNDIRECTED = "]-"
_REACH_TAIL_FORWARD = "]->"


def _reach_pattern(depth: int, *, forward: bool = False) -> str:
    """The variable-length reach pattern — the ONE string-formatting site.

    ``forward`` (`GQ-10`, semantics version 1.2.0; ledger row ``24.5-L-06``)
    selects the pattern's tail between :data:`_REACH_TAIL_FORWARD` and
    :data:`_REACH_TAIL_UNDIRECTED` — a choice between two constants, so the
    direction is never formatted into the text; only the depth is.

    Cypher variable-length bounds cannot be driver parameters (research
    assumption A2, re-verified against the live server at plan 15.2-12
    execution — both classic and quantified forms reject a parameter), so
    the depth is inlined as a literal. This is the single named, documented
    exception to the everything-is-a-parameter rule (15.2-RESEARCH.md
    Pitfall 7; threat T-15.2-01), and it admits exactly one value shape: a
    genuine ``int`` (``bool`` refused), at least 1 (depth 0 never reaches
    this function — the walk is skipped and the starting points are the
    answer), and at most :data:`MAX_DEPTH_CEILING` (over-ceiling queries
    never reach this function either — the translation declines and the
    fallback answers under D-04). Replay is unaffected: the pinned value is
    ``content_hash(GraphQuery)``, never the rendered Cypher (`GQ-20` at
    docs/GRAPH_QUERY_SEMANTICS.md:391).

    Raises:
        ValueError: the caller broke the validation contract above — an
            internal invariant violation, never a query-vocabulary refusal.
    """
    if (
        not isinstance(depth, int)
        or isinstance(depth, bool)
        or depth < 1
        or depth > MAX_DEPTH_CEILING
    ):
        raise ValueError(
            f"traversal depth literal must be an int in [1, "
            f"{MAX_DEPTH_CEILING}]; got {depth!r} — callers gate depth 0 and "
            "the over-ceiling decline before rendering (15.2-RESEARCH.md "
            "Pitfall 7)"
        )
    tail = _REACH_TAIL_FORWARD if forward else _REACH_TAIL_UNDIRECTED
    return f"-[:CCF_EDGE*1..{depth}" + tail


class Neo4jGraphReader(BaseGraphReader):
    """``GraphReader`` over a Neo4j driver — dialect and rows only.

    Identical semantics to every other backend reader by construction: the
    five acquisition statements below are Cypher renderings of the same five
    reads the SQL backends express, the rows they answer are plain dicts
    satisfying :class:`ccf.graph.reader.Row`, and everything above the rows
    — lineage-at-boundary, supersession-as-of, record construction, view
    ordering — is inherited from :class:`ccf.graph.reader.BaseGraphReader`
    and the substrate-neutral materialization core, so the semantics cannot
    fork here (15.2-RESEARCH.md Pitfall 5).

    The reader holds the Cypher ``GraphQuery`` translation:
    :meth:`_translate_query` answers whole queries natively — as-of,
    validity, and policy predicates over the write-time projections,
    ``allowed_entities`` membership as a driver list parameter, and
    bounded undirected traversal as a variable-length ``MATCH`` with hop
    admissibility enforced by path predicates — and the CI neo4j leg
    holds the translated answers byte-identical to the fallback (`GQ-31`
    at docs/GRAPH_QUERY_SEMANTICS.md:573). The one declined shape is an
    over-ceiling ``depth_limit`` (:data:`MAX_DEPTH_CEILING`), answered by
    the fallback instead (D-04): under a declined translation the
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

    def _translate_query(
        self, q: GraphQuery
    ) -> tuple[Sequence[Row], Sequence[Row]] | None:
        """Answer the whole query natively in Cypher (plan 15.2-12).

        The hook contract is all-or-nothing (`GQ-32` at
        docs/GRAPH_QUERY_SEMANTICS.md:583): the return is the complete
        answer's row pair — every predicate family applied, hop
        admissibility applied, ``allowed_entities`` membership applied.
        Three statements run inside one read transaction:

        1. **survivors** — the surviving entity claims: the as-of cut
           (`GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148, INV-CH7-14) as
           canonical-text comparison, the validity window (`GQ-09`) over
           the write-time re-renderings, policy admissibility (`GQ-08`)
           via parameterized dynamic property access, and the uniform
           rule's set membership (`GQ-15`) as a driver list parameter;
        2. **edges** — the surviving relationship claims that may appear
           in the answer, and on a traverse query the walk's whole
           expansion surface: permitted types (as a parameter over the
           projected property, never a Cypher type pattern), the induced
           subgraph under ``allowed_entities`` (`GQ-16`), and endpoint
           closure against the materialized survivors on every
           constrained answer;
        3. **walk** (traverse only, ``depth_limit >= 1``) — the bounded
           typed undirected expansion (`GQ-10`, INV-CH7-24) as a Cypher
           variable-length ``MATCH``, hop admissibility enforced by
           ``all(…)`` path predicates over every node and edge (`GQ-13`)
           with the allowed set stated explicitly as a driver list
           parameter. Walk starting points are computed within survivors
           (`GQ-11`) — seed classes select within the set, explicit seeds
           intersect with it — and the reached set filters both row sets,
           mirroring the SQL adapters' outer walk-membership SELECTs.

        The single value ever inlined into statement text is the
        validated depth literal (:func:`_reach_pattern` — the Pitfall-7
        exception). Two shapes short-circuit without a round trip: the
        empty ``allowed_entities`` set IS the empty answer (`GQ-04` at
        docs/GRAPH_QUERY_SEMANTICS.md:98), and an over-ceiling
        ``depth_limit`` declines to the fallback — still answered, per
        D-04 (`GQ-29`): the ceiling bounds Cypher text, never the
        vocabulary. ``admitted_entity_classes`` (`GQ-10` at
        docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0) is HONORED in Python:
        the path predicate gains ``$admissible`` — admitted-class survivors
        plus the starts — as a separate parameter (:data:`_WALK_NODES_ADMITTED`).
        ``direction`` (`GQ-10`, 1.2.0; ledger row ``24.5-L-06``) is HONORED
        natively: relationships are directed at write, so the forward walk
        is the reach pattern with its arrow — :func:`_reach_pattern` picks
        the tail between two constants; the direction is never rendered —
        and the differential suite holds the answer to the fallback over
        ``tests/conformance/query_corpus.py::direction_cases``.
        """
        if q.allowed_entities is not None and not q.allowed_entities:
            # The empty survivor set IS the answer (`GQ-04`): the empty
            # view, answered without a substrate round trip. An empty
            # answer is an answer, never an error (`GQ-23` at
            # docs/GRAPH_QUERY_SEMANTICS.md:474).
            return (), ()
        if (
            q.traverse is not None
            and q.traverse.depth_limit > MAX_DEPTH_CEILING
        ):
            # Decline → the fallback answers (D-04). Deliberately BEFORE
            # any session is opened: the decline is a pure function of the
            # query value.
            return None

        boundary = canonical_timestamp(q.as_of)
        policy_versions = q.permitted_policy_bundle_versions
        attribute_by_class = q.classification_attribute_by_class
        constrained = (
            q.allowed_entities is not None
            or policy_versions is not None
            or q.require_valid_at_boundary is not None
            or q.traverse is not None
        )
        require_validity = q.require_valid_at_boundary is True

        params: dict[str, object] = {
            "tenant": q.tenant_id,
            "boundary": boundary,
        }
        survivor_text = [_SURVIVORS_MATCH]
        edge_text = [_EDGES_MATCH]
        if require_validity:
            survivor_text.append(_ENTITY_VALIDITY)
            edge_text.append(_EDGE_VALIDITY)
        if policy_versions is not None:
            assert attribute_by_class is not None  # noqa: S101 - GQ-02 whole family
            assert q.permitted_classifications is not None  # noqa: S101
            survivor_text.append(_ENTITY_POLICY)
            edge_text.append(_EDGE_POLICY)
            params["policy_versions"] = sorted(policy_versions)
            # Prefixed property keys computed HERE, in Python: the
            # artifact-authored attribute name is data inside a map
            # parameter, resolved by dynamic property access on the server.
            params["attribute_by_class"] = {
                entity_class: ATTRIBUTE_PROPERTY_PREFIX + attribute
                for entity_class, attribute in attribute_by_class.items()
            }
            params["classifications"] = sorted(q.permitted_classifications)
        if q.allowed_entities is not None:
            survivor_text.append(_ENTITY_ALLOWED)
            edge_text.append(_EDGE_ALLOWED)
            params["allowed"] = sorted(q.allowed_entities)
        if q.traverse is not None:
            edge_text.append(_EDGE_TYPES)
            params["types"] = sorted(q.traverse.relationship_types)
        if constrained:
            edge_text.append(_EDGE_CLOSURE)
        survivor_text.append(_SURVIVORS_RETURN)
        edge_text.append(_EDGES_RETURN)

        def answer_whole_query(
            tx: Any,
        ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            entity_rows: list[dict[str, Any]] = [
                dict(record)
                for record in tx.run("".join(survivor_text), params)
            ]
            params["survivors"] = [row["entity_uri"] for row in entity_rows]
            relationship_rows: list[dict[str, Any]] = [
                dict(record) for record in tx.run("".join(edge_text), params)
            ]
            if q.traverse is None:
                return entity_rows, relationship_rows
            # Walk-start selection within survivors (`GQ-11` at
            # docs/GRAPH_QUERY_SEMANTICS.md:221): seed classes select
            # within the surviving universe; explicit seeds intersect with
            # it — a URI naming nothing in scope contributes no start.
            survivor_uris = {row["entity_uri"] for row in entity_rows}
            starts = {
                row["entity_uri"]
                for row in entity_rows
                if row["entity_class"] in q.traverse.seed_entity_classes
            }
            if q.seeds is not None:
                starts |= set(q.seeds) & survivor_uris
            reached = set(starts)
            if starts and q.traverse.depth_limit >= 1:
                # depth_limit=0 skips MATCH entirely: the walk starting
                # points only — a legal bound, not an error (`GQ-10` at
                # docs/GRAPH_QUERY_SEMANTICS.md:201).
                walk_text = [
                    _WALK_MATCH_PREFIX,
                    _reach_pattern(
                        q.traverse.depth_limit,
                        forward=q.traverse.direction == "forward",
                    ),
                    _WALK_MATCH_SUFFIX,
                    _WALK_NODES_ALL,
                ]
                if q.allowed_entities is not None:
                    walk_text.append(_WALK_NODES_ALLOWED)
                if q.traverse.admitted_entity_classes is not None:
                    # HONORED in Python: the admissible node list is the
                    # survivors of an admitted class plus the starts (the
                    # seed is in `nodes(p)`, and `GQ-11` starts are never
                    # filtered by admission), passed as its own parameter
                    # beside `$survivors` — never a narrowed survivor list,
                    # which `_EDGE_CLOSURE` already consumed.
                    admitted = q.traverse.admitted_entity_classes
                    walk_text.append(_WALK_NODES_ADMITTED)
                    params["admissible"] = sorted(
                        starts
                        | {
                            row["entity_uri"]
                            for row in entity_rows
                            if row["entity_class"] in admitted
                        }
                    )
                walk_text.append(_WALK_EDGES_ALL)
                walk_text.append(_WALK_RETURN)
                params["starts"] = sorted(starts)
                params["crossable"] = sorted(
                    {row["relationship_key"] for row in relationship_rows}
                )
                reached |= {
                    record["entity_uri"]
                    for record in tx.run("".join(walk_text), params)
                }
            # The reached set filters both row sets — the Cypher analogue
            # of the SQL adapters' `IN (SELECT uri FROM walk)` outer
            # SELECTs; the walk itself ran in the engine.
            entity_rows = [
                row for row in entity_rows if row["entity_uri"] in reached
            ]
            relationship_rows = [
                row
                for row in relationship_rows
                if row["subject_uri"] in reached
                and row["object_uri"] in reached
            ]
            return entity_rows, relationship_rows

        params["partition"] = self._store.partition
        with self._store.session() as session:
            entity_rows, relationship_rows = session.execute_read(
                answer_whole_query
            )
            return entity_rows, relationship_rows
