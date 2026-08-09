"""The concrete graph write handle — layers 3 and 4 of the D-IMPL-41 stack.

DESIGN.md §2A.5.3; whitepaper §7.3 (append-only-with-supersession graph state)
and INV-CH7-10 (only the Assembly worker holds a write handle).

**Why this module is private and why every backend's writer belongs in it.**
The CINV-02 lint restricts imports of ``ccf.graph._writer`` to ``ccf.assembly``
and ``ccf.boot`` — the L2 worker and the composition root, and nothing else.
That restriction is worth exactly as much as the completeness of this module:
if a backend shipped its writer next to its reader, the lint would guard one
module while the actual write path lived somewhere unguarded. So the rule is
structural rather than stylistic — **a new backend adds a writer class here, it
does not add a writer module elsewhere.** :class:`SqliteGraphWriter` and
:class:`PostgresGraphWriter` are that rule honoured: both are here, and both
are the same algorithm. The same force applies one seam down: **a new backend
adds a :class:`_GraphTxn` class here, never elsewhere** — the typed operation
seam is part of the write path, and write code outside this module is write
code outside the guard.

**One algorithm, two dialects.** :class:`BaseGraphWriter` holds the whole write
semantic — content identity, lineage set-union, chain restitching, tenant-scope
refusal — and a backend contributes only its transaction handling and, for SQL
backends, its statements. Two hand-written copies of the supersession restitch
would be two chances to get late-arriving observations wrong, and the
conformance suite could only tell us *that* they disagreed, not which one was
right.

**Why the write seam is typed operations, not SQL text (Phase 15.2).**
:class:`BaseGraphWriter` drives :class:`_GraphTxn` — nine typed graph-write
operations — rather than executing SQL statement constants directly. The
resolution is entailed, not discretionary: D-05/D-06 lock that every substrate
adapter runs under conformance suites whose writes go through booted L2
("nothing constructs a writer"), and neither a dict store nor Neo4j nor Mongo
can execute SQL text. The alternative — interpreting the nine SQL constants
per backend — was considered and rejected: five ad-hoc SQL interpreters would
each be a private re-implementation of this module's semantics, which is the
exact drift the shared base exists to prevent. SQL backends satisfy the seam
through one shared adapter (:class:`_SqlGraphTxn`) that drives the dialect
``ClassVar`` statements unchanged; non-SQL backends implement the nine
operations natively.

**Remote-substrate constraint (D-IMPL-88).** The :class:`_GraphTxn` contract
MUST remain implementable by a remote substrate whose commit is a single
batched transaction (no held session). Concretely: no operation's contract
requires observing intra-transaction *committed* state, and every mutating
operation's rowcount is resolvable before commit — an adapter may read the
committed state once, buffer its operations, answer reads and rowcounts from
(committed state + its own buffer), and submit the buffer as one batch at
commit. INV-CH7-10 single-writer is what makes read-before-buffer sound: no
concurrent writer exists that could invalidate the pre-commit read between
buffering and commit.

The four layers, for the reader who arrives here first (DESIGN.md §2A.5.3):

1. *Interface split* — :class:`ccf.graph.protocols.GraphReader` and
   ``GraphWriter`` are separate Protocols, so a read-path constructor has no
   parameter that could accept a write handle.
2. *DI at boot* — :mod:`ccf.boot` constructs exactly one writer and injects it
   into the Assembly worker only.
3. *Static gate* — this module's import restriction, plus strict mypy, turn a
   write reference outside L2 into a CI failure.
4. *Runtime backstop* — :class:`BootToken`. A writer cannot be constructed
   without one, tokens are single-use, and a second token for the same graph
   raises before any writing can begin.

**Honest residual claim (D-IMPL-41, DESIGN.md §9).** Python cannot make
determined-insider evasion impossible. The claim strength here is exactly: *no
unforced path exists, and every forced path fails CI or fails at boot.*
Absolute prevention is not asserted.

Every statement below is parameterized; no SQL is assembled from f-strings.
Claim content is never updated and no row is ever deleted — the only columns
that change after insert are ``superseded_by`` / ``superseded_at``, which is
what supersession *is* (INV-CH7-04, INV-CH7-21).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import copy
import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from typing import Any, ClassVar, Protocol

import psycopg

from ccf.contracts.canonical import (
    canonical_bytes,
    canonical_timestamp,
    content_hash,
)
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.backends.fluree import (
    ADAPTER_CONTEXT,
    L_EDGE,
    L_ENTITY,
    L_ENTITY_CLAIM,
    L_LINEAGE,
    L_RELATIONSHIP_CLAIM,
    LINK_PREDICATE,
    P_ADMIT_KEY,
    P_CLAIM_ID,
    P_CLAIM_JSON,
    P_CLAIM_KIND,
    P_ENTITY_CLASS,
    P_ENTITY_URI,
    P_ENTRY_JSON,
    P_FIRST_OBSERVED_AT,
    P_LAST_OBSERVED_AT,
    P_LINEAGE_ID,
    P_NODE_KEY,
    P_OBJECT_URI,
    P_OBSERVED_AT,
    P_PARTITION,
    P_POLICY_KEY,
    P_POLICY_VERSION,
    P_RELATIONSHIP_KEY,
    P_RELATIONSHIP_TYPE,
    P_SEQ,
    P_SUBJECT_URI,
    P_SUPERSEDED_AT,
    P_SUPERSEDED_BY,
    P_TENANT,
    P_VALID_FROM_CMP,
    P_VALID_TO_CMP,
    FlureeGraphStore,
    _mint_id,
    attribute_predicate,
)
from ccf.graph.backends.memory import (
    EntityClaimRow,
    EntityNodeRow,
    LineageRow,
    MemoryGraphStore,
    RelationshipClaimRow,
    RelationshipNodeRow,
    TenantState,
)
from ccf.graph.backends.mongo import (
    ENTITY_CLAIMS,
    ENTITY_NODES,
    LINEAGE,
    RELATIONSHIP_CLAIMS,
    RELATIONSHIP_NODES,
    TRAVERSAL_EDGES,
    MongoGraphStore,
    attribute_field_path,
)
from ccf.graph.backends.neo4j import (
    ATTRIBUTE_PROPERTY_PREFIX,
    Neo4jGraphStore,
)
from ccf.graph.backends.postgres import PostgresGraphStore
from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.protocols import UpsertResult
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, Row, parse_timestamp

__ccf_mode__ = "algorithmic"

__all__ = [
    "BootToken",
    "FlureeGraphWriter",
    "MemoryGraphWriter",
    "MongoGraphWriter",
    "Neo4jGraphWriter",
    "PostgresGraphWriter",
    "SingleWriterViolation",
    "SqliteGraphWriter",
    "mint_boot_token",
]


class SingleWriterViolation(RuntimeError):
    """An attempt was made to obtain a second write handle to a graph.

    Raised at boot rather than at first write: a violation that surfaces only
    when the second writer happens to write is a violation that reaches
    production.
    """


# Graph identities that currently have a live writer. Process-scoped state, and
# the only mutable module-level state in the fabric core — it exists because
# "how many writers are there?" is not a question a type system can answer.
_LIVE_WRITERS: set[str] = set()

# Only this module can produce a token, and only holders of this object can
# construct one. It is not exported.
_MINT_KEY = object()


class BootToken:
    """A single-use capability to construct one graph writer.

    Minted only by :func:`mint_boot_token`, which is itself reachable only from
    ``ccf.boot`` (CINV-02). Constructing a token directly raises, so "just
    make a token" is not an available workaround for a component that wants a
    writer it should not have.
    """

    def __init__(self, *, graph_identity: str, mint_key: object) -> None:
        if mint_key is not _MINT_KEY:
            raise SingleWriterViolation(
                "BootToken is mintable only by the composition root "
                "(ccf.boot); see DESIGN.md §2A.5.3"
            )
        self._graph_identity = graph_identity
        self._consumed = False

    @property
    def graph_identity(self) -> str:
        return self._graph_identity

    def consume(self) -> str:
        """Spend the token, returning the graph identity it authorizes.

        Raises:
            SingleWriterViolation: the token was already spent. One token, one
                writer — reuse is the same violation as a second mint.
        """
        if self._consumed:
            raise SingleWriterViolation(
                "boot token already consumed; a token authorizes exactly one "
                "GraphWriter"
            )
        self._consumed = True
        return self._graph_identity


def mint_boot_token(*, graph_identity: str) -> BootToken:
    """Mint the one token authorizing a writer over ``graph_identity``.

    Raises:
        SingleWriterViolation: a live writer already exists for this graph.
    """
    if graph_identity in _LIVE_WRITERS:
        raise SingleWriterViolation(
            f"a GraphWriter already exists for graph {graph_identity!r}; "
            "the fabric permits exactly one writer per graph (INV-CH7-10)"
        )
    _LIVE_WRITERS.add(graph_identity)
    return BootToken(graph_identity=graph_identity, mint_key=_MINT_KEY)


def _entity_content_key(claim: EntityClaim) -> dict[str, object]:
    """The fields that make one entity claim the *same claim* as another.

    Lineage is excluded because it grows: an identity that moved when a second
    source corroborated the claim would make "the same claim" unaddressable
    (INV-CH7-17). ``observed_at`` is excluded because re-observing unchanged
    state is corroboration, not a new claim — including it would manufacture a
    supersession every time a source repeated itself.
    """
    return {
        "tenant_id": claim.tenant_id,
        "entity_uri": claim.entity_uri,
        "entity_class": claim.entity_class,
        "attributes": dict(claim.attributes),
        "valid_from": claim.valid_from,
        "valid_to": claim.valid_to,
    }


def _relationship_content_key(claim: RelationshipClaim) -> dict[str, object]:
    """As :func:`_entity_content_key`, for the R axis."""
    return {
        "tenant_id": claim.tenant_id,
        "relationship_type": claim.relationship_type,
        "subject_uri": claim.subject_uri,
        "object_uri": claim.object_uri,
        "attributes": dict(claim.attributes),
        "valid_from": claim.valid_from,
        "valid_to": claim.valid_to,
    }


def _claim_payload(claim: EntityClaim | RelationshipClaim) -> str:
    """The persisted ``claim_json`` text, in the SDK's one canonical form.

    **D-IMPL-90 (Dave, 2026-08-08, option (a)).** This used to render
    ``claim.model_dump(mode="json", exclude={"lineage"})``, which preserves
    whatever UTC offset a claim was authored with — so the same instant had
    two renderings in the fabric at once: the pydantic one on disk and the
    UTC-normalized one every hash, boundary and answer uses
    (:func:`ccf.contracts.canonical.canonical_bytes`). The pushed `GQ-09`
    validity predicate compares canonical UTC *text* read out of this column,
    so an offset-authored claim rendered as NULL and was excluded from a
    pushed answer the fallback — comparing datetime *values* — included: a
    reachable counterexample to `GQ-31` byte-identity
    (docs/GRAPH_QUERY_SEMANTICS.md:573). Rendering the payload through the
    canonical serializer removes the second rendering at its source, for
    every adapter at once, rather than teaching each SQL dialect to order
    offsets.

    Nothing about claim *identity* moves: ``claim_id`` is
    ``content_hash(_entity_content_key(claim))``, which already passes the
    ``datetime`` value through the same canonical normalization — an
    offset-authored claim and a ``Z``-authored claim of the same instant
    always shared one content hash. Answer bytes do not move either: every
    answer is re-canonicalized on the way out of
    :mod:`ccf.graph.reader`. What changes is only the bytes at rest.

    Lineage is excluded because it is persisted per-entry in its own rows and
    re-attached at boundary by the reader; the field is walked back in on
    read (``payload["lineage"] = …``), so it must not be in the payload.
    """
    return canonical_bytes(
        {
            name: getattr(claim, name)
            for name in type(claim).model_fields
            if name != "lineage"
        }
    ).decode("utf-8")


def relationship_key(claim: RelationshipClaim) -> str:
    """Content identity of the edge ``(type, subject, object)`` triple.

    Relationship *type* is part of edge identity: two types over the same
    endpoints are two first-class edges with independent lineage, not one edge
    with a type attribute (INV-CH7-20).
    """
    return content_hash(
        {
            "relationship_type": claim.relationship_type,
            "subject_uri": claim.subject_uri,
            "object_uri": claim.object_uri,
        }
    )


class _Store(Protocol):
    """What the shared writer needs of a backend store: its identity."""

    @property
    def graph_identity(self) -> str: ...


class _Txn(Protocol):
    """One open SQL write transaction, in whichever dialect.

    The SQL-text seam under :class:`_SqlGraphTxn` — only the shared SQL adapter
    drives it; :class:`BaseGraphWriter` speaks :class:`_GraphTxn`. ``execute``
    returns the number of rows the statement actually changed — zero for an
    ignored duplicate. That number is the whole of how the writer distinguishes
    a new claim from a re-arrival, so it is part of the contract a backend
    implements rather than an incidental driver detail.
    """

    def execute(self, sql: str, params: tuple[object, ...]) -> int: ...

    def query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]: ...


class _GraphTxn(Protocol):
    """One open graph-write transaction: nine typed operations, no SQL.

    The write seam :class:`BaseGraphWriter` drives. SQL backends satisfy it
    through :class:`_SqlGraphTxn`; a dict-backed, Cypher-backed, or
    aggregation-backed transaction implements the nine operations natively.
    Implementations live in this module only (CINV-02 — see the module
    docstring).

    Two contract rules hold for every operation, and both exist so the seam
    stays implementable by a remote substrate whose commit is a single batched
    transaction with no held session (D-IMPL-88, module docstring):

    * **Mutating operations return rows actually changed, resolvable before
      commit.** Zero means an ignored duplicate — that number is the whole of
      how the writer distinguishes a new claim from a re-arrival. A batched
      adapter resolves it from (committed state read before buffering + its
      own buffer); INV-CH7-10 single-writer guarantees the pre-commit read
      cannot be invalidated concurrently.
    * **Reads see this transaction's own buffered operations, never another
      transaction's uncommitted state.** ``select_*_chain`` must include
      claims appended earlier in the *same* transaction; it never requires
      observing intra-transaction committed state.
    """

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        """Record one observation of the node, widening its observed window.

        ``first_observed_at`` only ever moves earlier and ``last_observed_at``
        only ever moves later; nothing is deleted. Returns rows changed
        (resolvable before commit); the writer does not condition on it.
        """
        ...

    def insert_entity_claim(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        """Append a claim, ignoring an exact re-arrival.

        Returns 1 for a new claim and 0 for a re-arrival of one already held
        under ``(tenant_id, entity_uri, claim_id)`` — resolvable before
        commit, and the writer's idempotency branch depends on it.
        """
        ...

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        """The node's whole claim chain, oldest first.

        Rows expose ``claim_id`` and ``observed_at``; ordering is by
        ``observed_at``, ties broken by arrival order. Includes claims
        appended earlier in this same transaction (own buffer, not another
        transaction's committed state).
        """
        ...

    def update_entity_supersession(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        """Set (or clear, with ``None``) one claim's supersession edge.

        The only mutation ever applied to an existing claim (INV-CH7-04).
        Returns rows changed, resolvable before commit.
        """
        ...

    def upsert_relationship_node(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        relationship_type: str,
        subject_uri: str,
        object_uri: str,
        observed_at: str,
    ) -> int:
        """As :meth:`upsert_entity_node`, for the R axis."""
        ...

    def insert_relationship_claim(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        """As :meth:`insert_entity_claim`, keyed on the relationship key."""
        ...

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        """As :meth:`select_entity_chain`, for the R axis."""
        ...

    def update_relationship_supersession(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        """As :meth:`update_entity_supersession`, for the R axis."""
        ...

    def insert_lineage(
        self,
        *,
        tenant_id: str,
        claim_kind: str,
        node_key: str,
        claim_id: str,
        lineage_id: str,
        entry_json: str,
    ) -> int:
        """Append one lineage entry, ignoring one already recorded.

        Returns 1 for a new entry and 0 for a collision on the full entry
        identity ``(tenant_id, claim_kind, node_key, claim_id, lineage_id)``
        — resolvable before commit. Ignore-on-conflict here *is* the L-axis
        set-union (INV-CH7-17).
        """
        ...


class _SetSupersession(Protocol):
    """Apply one supersession edge during a chain restitch.

    Binds the node coordinates (tenant, key) so :meth:`BaseGraphWriter.
    _restitch_chain` stays one implementation over both axes.
    """

    def __call__(
        self,
        *,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int: ...


class BaseGraphWriter:
    """The single ``GraphWriter`` over one graph — semantics, minus the substrate.

    Whitepaper §7.3; DESIGN.md §2A.5.3/§2A.5.4 step 4. Structurally conforms to
    :class:`ccf.graph.protocols.GraphWriter`. Drives :class:`_GraphTxn` typed
    operations only — no SQL text leaves this class, which is what lets a
    non-SQL backend subclass it without interpreting SQL.

    Args:
        store: The backend whose graph this writer mutates.
        token: The boot token authorizing this writer. Required, keyword-only,
            and single-use — omitting it is a ``TypeError`` and forging it is a
            :class:`SingleWriterViolation`.

    Raises:
        SingleWriterViolation: ``token`` is not a real token, was already
            spent, or authorizes a different graph than ``store``.
    """

    # The SQL dialect surface. Consumed only by :class:`_SqlGraphTxn`; nothing
    # in this class reads these, and a non-SQL backend leaves them unset.

    #: Node-identity upsert. Widens the observed-time window; never deletes.
    UPSERT_ENTITY_NODE: ClassVar[str]
    #: Append a claim, ignoring an exact re-arrival.
    INSERT_ENTITY_CLAIM: ClassVar[str]
    #: The node's whole claim chain in observed-time order.
    SELECT_ENTITY_CHAIN: ClassVar[str]
    #: Set (or clear) one claim's supersession edge.
    UPDATE_ENTITY_SUPERSESSION: ClassVar[str]
    UPSERT_RELATIONSHIP_NODE: ClassVar[str]
    INSERT_RELATIONSHIP_CLAIM: ClassVar[str]
    SELECT_RELATIONSHIP_CHAIN: ClassVar[str]
    UPDATE_RELATIONSHIP_SUPERSESSION: ClassVar[str]
    #: Append one lineage entry, ignoring one already recorded.
    INSERT_LINEAGE: ClassVar[str]

    def __init__(self, *, store: _Store, token: BootToken) -> None:
        if not isinstance(token, BootToken):
            raise SingleWriterViolation(
                "a GraphWriter requires a BootToken minted by the composition "
                "root (ccf.boot); see DESIGN.md §2A.5.3"
            )
        if token.graph_identity != store.graph_identity:
            raise SingleWriterViolation(
                "boot token authorizes a different graph than the store it was "
                "paired with"
            )
        self._graph_identity = token.consume()
        self._closed = False

    def _check_open(self) -> None:
        if self._closed:
            raise SingleWriterViolation(
                "this GraphWriter has been closed; obtain a new fabric through "
                "the composition root"
            )

    def _transaction(self) -> AbstractContextManager[_GraphTxn]:
        """Open one all-or-nothing write transaction."""
        raise NotImplementedError

    def close(self) -> None:
        """Retire this writer and release its graph for a subsequent boot.

        Shutdown, not an escape hatch: the writer refuses every further write,
        so this cannot be used to hold two usable writers at once.
        """
        if self._closed:
            return
        self._closed = True
        _LIVE_WRITERS.discard(self._graph_identity)

    def _write_lineage(
        self,
        txn: _GraphTxn,
        *,
        tenant_id: str,
        kind: str,
        node_key: str,
        claim_id: str,
        entries: frozenset[LineageEntry],
    ) -> int:
        """Accumulate lineage by set-union; return how many entries were new.

        Ignore-on-conflict against the full entry identity *is* the set-union:
        a re-delivered envelope collides and is dropped, a second source does
        not (INV-CH7-17). Nothing here overwrites — an ``UPDATE`` of a lineage
        column would satisfy an idempotence test while destroying the
        multi-source evidence the L axis exists to hold.
        """
        added = 0
        for entry in entries:
            added += txn.insert_lineage(
                tenant_id=tenant_id,
                claim_kind=kind,
                node_key=node_key,
                claim_id=claim_id,
                lineage_id=content_hash(entry),
                entry_json=json.dumps(entry.model_dump(mode="json"), sort_keys=True),
            )
        return added

    @staticmethod
    def _restitch_chain(
        chain: Sequence[Row],
        *,
        set_supersession: _SetSupersession,
        new_claim_id: str,
    ) -> str | None:
        """Recompute the supersession chain for one node by observed-time.

        ``chain`` is the node's whole claim chain as ``select_*_chain``
        returns it — including the claim appended earlier in this transaction.
        Rewriting the whole chain rather than only linking the newest claim is
        what makes late-arriving observations behave: a claim observed
        *before* the current one slots into history already superseded,
        instead of wrongly displacing state the fabric learned later. The
        operation is idempotent, so a replayed write leaves the chain
        untouched.

        Returns the ``claim_id`` this write superseded, if any.
        """
        superseded: str | None = None
        for position, row in enumerate(chain):
            is_last = position == len(chain) - 1
            successor = None if is_last else chain[position + 1]["claim_id"]
            successor_at = None if is_last else chain[position + 1]["observed_at"]
            set_supersession(
                claim_id=row["claim_id"],
                superseded_by=successor,
                superseded_at=successor_at,
            )
            if row["claim_id"] == new_claim_id and position > 0:
                superseded = chain[position - 1]["claim_id"]
        return superseded

    @staticmethod
    def _require_scope(*, tenant_id: str, claim_tenant_id: str) -> None:
        if tenant_id != claim_tenant_id:
            raise ValueError(
                f"claim tenant {claim_tenant_id!r} disagrees with the call's "
                f"tenant scope {tenant_id!r}; the fabric refuses rather than "
                "picking one (INV-CH7-16)"
            )

    def upsert_entity(
        self,
        *,
        tenant_id: str,
        claim: EntityClaim,
        policy_bundle_version: str,
    ) -> UpsertResult:
        """Idempotently upsert an entity claim, accumulating lineage by union."""
        self._require_scope(tenant_id=tenant_id, claim_tenant_id=claim.tenant_id)
        self._check_open()
        claim_id = content_hash(_entity_content_key(claim))
        observed_at = canonical_timestamp(claim.observed_at)
        payload = _claim_payload(claim)
        with self._transaction() as txn:
            txn.upsert_entity_node(
                tenant_id=tenant_id,
                entity_uri=claim.entity_uri,
                entity_class=claim.entity_class,
                observed_at=observed_at,
            )
            created = (
                txn.insert_entity_claim(
                    tenant_id=tenant_id,
                    entity_uri=claim.entity_uri,
                    claim_id=claim_id,
                    claim_json=payload,
                    observed_at=observed_at,
                    policy_bundle_version=policy_bundle_version,
                )
                == 1
            )
            lineage_added = self._write_lineage(
                txn,
                tenant_id=tenant_id,
                kind=ENTITY_KIND,
                node_key=claim.entity_uri,
                claim_id=claim_id,
                entries=claim.lineage,
            )

            def _set_supersession(
                *,
                claim_id: str,
                superseded_by: str | None,
                superseded_at: str | None,
            ) -> int:
                return txn.update_entity_supersession(
                    tenant_id=tenant_id,
                    entity_uri=claim.entity_uri,
                    claim_id=claim_id,
                    superseded_by=superseded_by,
                    superseded_at=superseded_at,
                )

            superseded = (
                self._restitch_chain(
                    txn.select_entity_chain(
                        tenant_id=tenant_id, entity_uri=claim.entity_uri
                    ),
                    set_supersession=_set_supersession,
                    new_claim_id=claim_id,
                )
                if created
                else None
            )
        return UpsertResult(
            node_key=claim.entity_uri,
            claim_id=claim_id,
            claim_created=created,
            lineage_added=lineage_added,
            superseded_claim_id=superseded,
        )

    def upsert_relationship(
        self,
        *,
        tenant_id: str,
        claim: RelationshipClaim,
        policy_bundle_version: str,
    ) -> UpsertResult:
        """Idempotently upsert a relationship claim, with per-edge lineage."""
        self._require_scope(tenant_id=tenant_id, claim_tenant_id=claim.tenant_id)
        self._check_open()
        key = relationship_key(claim)
        claim_id = content_hash(_relationship_content_key(claim))
        observed_at = canonical_timestamp(claim.observed_at)
        payload = _claim_payload(claim)
        with self._transaction() as txn:
            txn.upsert_relationship_node(
                tenant_id=tenant_id,
                relationship_key=key,
                relationship_type=claim.relationship_type,
                subject_uri=claim.subject_uri,
                object_uri=claim.object_uri,
                observed_at=observed_at,
            )
            created = (
                txn.insert_relationship_claim(
                    tenant_id=tenant_id,
                    relationship_key=key,
                    claim_id=claim_id,
                    claim_json=payload,
                    observed_at=observed_at,
                    policy_bundle_version=policy_bundle_version,
                )
                == 1
            )
            lineage_added = self._write_lineage(
                txn,
                tenant_id=tenant_id,
                kind=RELATIONSHIP_KIND,
                node_key=key,
                claim_id=claim_id,
                entries=claim.lineage,
            )

            def _set_supersession(
                *,
                claim_id: str,
                superseded_by: str | None,
                superseded_at: str | None,
            ) -> int:
                return txn.update_relationship_supersession(
                    tenant_id=tenant_id,
                    relationship_key=key,
                    claim_id=claim_id,
                    superseded_by=superseded_by,
                    superseded_at=superseded_at,
                )

            superseded = (
                self._restitch_chain(
                    txn.select_relationship_chain(
                        tenant_id=tenant_id, relationship_key=key
                    ),
                    set_supersession=_set_supersession,
                    new_claim_id=claim_id,
                )
                if created
                else None
            )
        return UpsertResult(
            node_key=key,
            claim_id=claim_id,
            claim_created=created,
            lineage_added=lineage_added,
            superseded_claim_id=superseded,
        )


class _SqlGraphTxn:
    """The nine :class:`_GraphTxn` operations over one SQL dialect.

    The one place typed operations meet SQL text: each operation executes the
    concrete writer's dialect ``ClassVar`` statement through the underlying
    :class:`_Txn`. Both SQL backends share this adapter unchanged — the
    dialect difference lives entirely in the statements, exactly as before the
    typed seam existed. Rowcounts pass through from ``_Txn.execute``, whose
    contract (zero = ignored duplicate) is the same contract
    :class:`_GraphTxn` states.
    """

    def __init__(self, *, txn: _Txn, statements: type[BaseGraphWriter]) -> None:
        self._txn = txn
        self._statements = statements

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        return self._txn.execute(
            self._statements.UPSERT_ENTITY_NODE,
            (tenant_id, entity_uri, entity_class, observed_at, observed_at),
        )

    def insert_entity_claim(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        return self._txn.execute(
            self._statements.INSERT_ENTITY_CLAIM,
            (
                tenant_id,
                entity_uri,
                claim_id,
                claim_json,
                observed_at,
                policy_bundle_version,
            ),
        )

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        return self._txn.query(
            self._statements.SELECT_ENTITY_CHAIN, (tenant_id, entity_uri)
        )

    def update_entity_supersession(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        return self._txn.execute(
            self._statements.UPDATE_ENTITY_SUPERSESSION,
            (superseded_by, superseded_at, tenant_id, entity_uri, claim_id),
        )

    def upsert_relationship_node(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        relationship_type: str,
        subject_uri: str,
        object_uri: str,
        observed_at: str,
    ) -> int:
        return self._txn.execute(
            self._statements.UPSERT_RELATIONSHIP_NODE,
            (
                tenant_id,
                relationship_key,
                relationship_type,
                subject_uri,
                object_uri,
                observed_at,
                observed_at,
            ),
        )

    def insert_relationship_claim(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        return self._txn.execute(
            self._statements.INSERT_RELATIONSHIP_CLAIM,
            (
                tenant_id,
                relationship_key,
                claim_id,
                claim_json,
                observed_at,
                policy_bundle_version,
            ),
        )

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        return self._txn.query(
            self._statements.SELECT_RELATIONSHIP_CHAIN,
            (tenant_id, relationship_key),
        )

    def update_relationship_supersession(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        return self._txn.execute(
            self._statements.UPDATE_RELATIONSHIP_SUPERSESSION,
            (superseded_by, superseded_at, tenant_id, relationship_key, claim_id),
        )

    def insert_lineage(
        self,
        *,
        tenant_id: str,
        claim_kind: str,
        node_key: str,
        claim_id: str,
        lineage_id: str,
        entry_json: str,
    ) -> int:
        return self._txn.execute(
            self._statements.INSERT_LINEAGE,
            (tenant_id, claim_kind, node_key, claim_id, lineage_id, entry_json),
        )


class _SqliteTxn:
    """``_Txn`` over a ``sqlite3`` connection inside a ``with connection`` block."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def execute(self, sql: str, params: tuple[object, ...]) -> int:
        cursor = self._connection.execute(sql, params)
        return max(cursor.rowcount, 0)

    def query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        return self._connection.execute(sql, params).fetchall()


class SqliteGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one SQLite graph — the D-IMPL-02 dev backend."""

    UPSERT_ENTITY_NODE: ClassVar[str] = """
        INSERT INTO entities (
            tenant_id, entity_uri, entity_class, first_observed_at,
            last_observed_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, entity_uri) DO UPDATE SET
            first_observed_at =
                MIN(entities.first_observed_at, excluded.first_observed_at),
            last_observed_at =
                MAX(entities.last_observed_at, excluded.last_observed_at)
    """
    INSERT_ENTITY_CLAIM: ClassVar[str] = """
        INSERT INTO entity_claims (
            tenant_id, entity_uri, claim_id, claim_json, observed_at,
            policy_bundle_version
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, entity_uri, claim_id) DO NOTHING
    """
    SELECT_ENTITY_CHAIN: ClassVar[str] = """
        SELECT claim_id, observed_at FROM entity_claims
        WHERE tenant_id = ? AND entity_uri = ?
        ORDER BY observed_at, rowid
    """
    UPDATE_ENTITY_SUPERSESSION: ClassVar[str] = """
        UPDATE entity_claims SET superseded_by = ?, superseded_at = ?
        WHERE tenant_id = ? AND entity_uri = ? AND claim_id = ?
    """
    UPSERT_RELATIONSHIP_NODE: ClassVar[str] = """
        INSERT INTO relationships (
            tenant_id, relationship_key, relationship_type, subject_uri,
            object_uri, first_observed_at, last_observed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, relationship_key) DO UPDATE SET
            first_observed_at =
                MIN(relationships.first_observed_at, excluded.first_observed_at),
            last_observed_at =
                MAX(relationships.last_observed_at, excluded.last_observed_at)
    """
    INSERT_RELATIONSHIP_CLAIM: ClassVar[str] = """
        INSERT INTO relationship_claims (
            tenant_id, relationship_key, claim_id, claim_json, observed_at,
            policy_bundle_version
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, relationship_key, claim_id) DO NOTHING
    """
    SELECT_RELATIONSHIP_CHAIN: ClassVar[str] = """
        SELECT claim_id, observed_at FROM relationship_claims
        WHERE tenant_id = ? AND relationship_key = ?
        ORDER BY observed_at, rowid
    """
    UPDATE_RELATIONSHIP_SUPERSESSION: ClassVar[str] = """
        UPDATE relationship_claims SET superseded_by = ?, superseded_at = ?
        WHERE tenant_id = ? AND relationship_key = ? AND claim_id = ?
    """
    INSERT_LINEAGE: ClassVar[str] = """
        INSERT INTO lineage (
            tenant_id, claim_kind, node_key, claim_id, lineage_id, entry_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (tenant_id, claim_kind, node_key, claim_id, lineage_id)
        DO NOTHING
    """

    def __init__(self, *, store: SqliteGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        connection = self._store.connection
        with connection:
            yield _SqlGraphTxn(txn=_SqliteTxn(connection), statements=type(self))


class _PostgresTxn:
    """``_Txn`` over a psycopg cursor inside an explicit transaction."""

    def __init__(self, cursor: psycopg.Cursor[dict[str, Any]]) -> None:
        self._cursor = cursor

    def execute(self, sql: str, params: tuple[object, ...]) -> int:
        self._cursor.execute(sql.encode(), params)
        return max(self._cursor.rowcount, 0)

    def query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        self._cursor.execute(sql.encode(), params)
        return self._cursor.fetchall()


class PostgresGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one Postgres graph — the D-IMPL-02 production backend.

    Same algorithm as :class:`SqliteGraphWriter`, inherited rather than
    restated. What differs is dialect: ``%s`` placeholders,
    ``LEAST``/``GREATEST`` for the observed-time window, and ``seq`` where
    SQLite reads ``rowid``.
    """

    UPSERT_ENTITY_NODE: ClassVar[str] = """
        INSERT INTO entities (
            tenant_id, entity_uri, entity_class, first_observed_at,
            last_observed_at
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, entity_uri) DO UPDATE SET
            first_observed_at =
                LEAST(entities.first_observed_at, excluded.first_observed_at),
            last_observed_at =
                GREATEST(entities.last_observed_at, excluded.last_observed_at)
    """
    INSERT_ENTITY_CLAIM: ClassVar[str] = """
        INSERT INTO entity_claims (
            tenant_id, entity_uri, claim_id, claim_json, observed_at,
            policy_bundle_version
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, entity_uri, claim_id) DO NOTHING
    """
    SELECT_ENTITY_CHAIN: ClassVar[str] = """
        SELECT claim_id, observed_at FROM entity_claims
        WHERE tenant_id = %s AND entity_uri = %s
        ORDER BY observed_at, seq
    """
    UPDATE_ENTITY_SUPERSESSION: ClassVar[str] = """
        UPDATE entity_claims SET superseded_by = %s, superseded_at = %s
        WHERE tenant_id = %s AND entity_uri = %s AND claim_id = %s
    """
    UPSERT_RELATIONSHIP_NODE: ClassVar[str] = """
        INSERT INTO relationships (
            tenant_id, relationship_key, relationship_type, subject_uri,
            object_uri, first_observed_at, last_observed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, relationship_key) DO UPDATE SET
            first_observed_at =
                LEAST(relationships.first_observed_at,
                      excluded.first_observed_at),
            last_observed_at =
                GREATEST(relationships.last_observed_at,
                         excluded.last_observed_at)
    """
    INSERT_RELATIONSHIP_CLAIM: ClassVar[str] = """
        INSERT INTO relationship_claims (
            tenant_id, relationship_key, claim_id, claim_json, observed_at,
            policy_bundle_version
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, relationship_key, claim_id) DO NOTHING
    """
    SELECT_RELATIONSHIP_CHAIN: ClassVar[str] = """
        SELECT claim_id, observed_at FROM relationship_claims
        WHERE tenant_id = %s AND relationship_key = %s
        ORDER BY observed_at, seq
    """
    UPDATE_RELATIONSHIP_SUPERSESSION: ClassVar[str] = """
        UPDATE relationship_claims SET superseded_by = %s, superseded_at = %s
        WHERE tenant_id = %s AND relationship_key = %s AND claim_id = %s
    """
    INSERT_LINEAGE: ClassVar[str] = """
        INSERT INTO lineage (
            tenant_id, claim_kind, node_key, claim_id, lineage_id, entry_json
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, claim_kind, node_key, claim_id, lineage_id)
        DO NOTHING
    """

    def __init__(self, *, store: PostgresGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        connection = self._store.connection
        with connection.transaction(), connection.cursor() as cursor:
            yield _SqlGraphTxn(txn=_PostgresTxn(cursor), statements=type(self))


class _MemoryTxn:
    """The nine :class:`_GraphTxn` operations, natively over one memory store's dicts.

    The first non-SQL proof of the typed write seam (Phase 15.2 D-06): no SQL
    text exists here and none is interpreted — each operation mutates the
    store's per-tenant dicts directly. Lives in this module and only this
    module, per the CINV-02 rule the module docstring states: the typed
    operation seam is part of the write path.

    The two :class:`_GraphTxn` contract rules, honoured natively:

    * **Rowcounts resolve before commit.** ``insert_entity_claim`` /
      ``insert_relationship_claim`` return 0 for a re-arrival of a claim id
      already held — the writer's idempotency signal — and ``insert_lineage``
      returns 0 on a full-entry-identity collision, which *is* the L-axis
      set-union (INV-CH7-17).
    * **Reads see this transaction's own operations.** Mutations apply to the
      live dicts immediately, so ``select_*_chain`` includes claims appended
      earlier in the same transaction; single-writer (INV-CH7-10) guarantees
      no other transaction's state exists to leak in.

    All-or-nothing comes from the owning :class:`MemoryGraphWriter`
    transaction: each tenant's state is deep-copied before this transaction
    first touches it, and :meth:`rollback` restores those copies in place on
    exception.
    """

    def __init__(self, *, store: MemoryGraphStore) -> None:
        self._store = store
        self._snapshots: dict[str, TenantState] = {}

    def _state(self, tenant_id: str) -> TenantState:
        """The tenant's live tables, snapshotted on first touch for rollback."""
        state = self._store.tenant_state(tenant_id)
        if tenant_id not in self._snapshots:
            self._snapshots[tenant_id] = copy.deepcopy(state)
        return state

    def rollback(self) -> None:
        """Restore every touched tenant's tables to their pre-transaction state.

        In-place restoration, deliberately: the reader and any concurrent
        holder keep their reference to the same :class:`TenantState` object,
        so swapping the object out would leave them reading rolled-back
        state.
        """
        for tenant_id, copied in self._snapshots.items():
            live = self._store.tenant_state(tenant_id)
            live.entity_nodes.clear()
            live.entity_nodes.update(copied.entity_nodes)
            live.entity_claims.clear()
            live.entity_claims.update(copied.entity_claims)
            live.relationship_nodes.clear()
            live.relationship_nodes.update(copied.relationship_nodes)
            live.relationship_claims.clear()
            live.relationship_claims.update(copied.relationship_claims)
            live.lineage.clear()
            live.lineage.update(copied.lineage)

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        state = self._state(tenant_id)
        node = state.entity_nodes.get(entity_uri)
        if node is None:
            state.entity_nodes[entity_uri] = EntityNodeRow(
                entity_class=entity_class,
                first_observed_at=observed_at,
                last_observed_at=observed_at,
            )
            return 1
        # Canonical text compares lexicographically as chronologically, so
        # min/max widen the observed window exactly as MIN/MAX do in SQL.
        node["first_observed_at"] = min(node["first_observed_at"], observed_at)
        node["last_observed_at"] = max(node["last_observed_at"], observed_at)
        return 1

    def insert_entity_claim(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        state = self._state(tenant_id)
        claims = state.entity_claims.setdefault(entity_uri, {})
        if claim_id in claims:
            return 0
        claims[claim_id] = EntityClaimRow(
            entity_uri=entity_uri,
            claim_id=claim_id,
            claim_json=claim_json,
            observed_at=observed_at,
            policy_bundle_version=policy_bundle_version,
            superseded_by=None,
            superseded_at=None,
        )
        return 1

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        state = self._state(tenant_id)
        # Stable sort over dict insertion order: observed_at first, ties by
        # arrival — the memory rendering of ``ORDER BY observed_at, rowid``.
        return tuple(
            sorted(
                state.entity_claims.get(entity_uri, {}).values(),
                key=lambda row: row["observed_at"],
            )
        )

    def update_entity_supersession(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        state = self._state(tenant_id)
        row = state.entity_claims.get(entity_uri, {}).get(claim_id)
        if row is None:
            return 0
        row["superseded_by"] = superseded_by
        row["superseded_at"] = superseded_at
        return 1

    def upsert_relationship_node(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        relationship_type: str,
        subject_uri: str,
        object_uri: str,
        observed_at: str,
    ) -> int:
        state = self._state(tenant_id)
        node = state.relationship_nodes.get(relationship_key)
        if node is None:
            state.relationship_nodes[relationship_key] = RelationshipNodeRow(
                relationship_type=relationship_type,
                subject_uri=subject_uri,
                object_uri=object_uri,
                first_observed_at=observed_at,
                last_observed_at=observed_at,
            )
            return 1
        node["first_observed_at"] = min(node["first_observed_at"], observed_at)
        node["last_observed_at"] = max(node["last_observed_at"], observed_at)
        return 1

    def insert_relationship_claim(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        state = self._state(tenant_id)
        claims = state.relationship_claims.setdefault(relationship_key, {})
        if claim_id in claims:
            return 0
        claims[claim_id] = RelationshipClaimRow(
            relationship_key=relationship_key,
            claim_id=claim_id,
            claim_json=claim_json,
            observed_at=observed_at,
            policy_bundle_version=policy_bundle_version,
            superseded_by=None,
            superseded_at=None,
        )
        return 1

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        state = self._state(tenant_id)
        return tuple(
            sorted(
                state.relationship_claims.get(relationship_key, {}).values(),
                key=lambda row: row["observed_at"],
            )
        )

    def update_relationship_supersession(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        state = self._state(tenant_id)
        row = state.relationship_claims.get(relationship_key, {}).get(claim_id)
        if row is None:
            return 0
        row["superseded_by"] = superseded_by
        row["superseded_at"] = superseded_at
        return 1

    def insert_lineage(
        self,
        *,
        tenant_id: str,
        claim_kind: str,
        node_key: str,
        claim_id: str,
        lineage_id: str,
        entry_json: str,
    ) -> int:
        state = self._state(tenant_id)
        entries = state.lineage.setdefault((claim_kind, node_key, claim_id), {})
        if lineage_id in entries:
            return 0
        entries[lineage_id] = LineageRow(entry_json=entry_json)
        return 1


class MemoryGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one in-memory graph — the D-06 KV floor.

    Same algorithm as :class:`SqliteGraphWriter` and
    :class:`PostgresGraphWriter`, inherited rather than restated. What differs
    is the transaction: :class:`_MemoryTxn` implements the nine typed
    operations natively over the store's per-tenant dicts, which is exactly
    what the typed seam exists to allow — no SQL ``ClassVar`` statements are
    set here, and nothing in :class:`BaseGraphWriter` reads them for a
    non-SQL backend (see the "typed operations, not SQL text" section of the
    module docstring).
    """

    def __init__(self, *, store: MemoryGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        txn = _MemoryTxn(store=self._store)
        try:
            yield txn
        except BaseException:
            txn.rollback()
            raise


# --- the Neo4j write path (plan 15.2-12) --------------------------------------
#
# The nine typed operations as parameterized Cypher, confined to this module
# per the CINV-02 rule the module docstring states: the typed operation seam
# is part of the write path, and write code outside this module is write code
# outside the guard (threat T-15.2-06). Every value below travels as a driver
# parameter; no statement text is assembled from values. The `CCF_EDGE`
# Cypher relationship type is fixed SDK vocabulary — the artifact-authored
# CCF relationship type travels as the `relationship_type` property, never
# rendered into a pattern (threat T-15.2-01).

#: The insertion-order counter — the graph rendering of SQLite's ``rowid`` /
#: Postgres's ``BIGSERIAL``. Per-partition, so each graph owns its own
#: arrival order. Single-writer (INV-CH7-10) makes the read-increment safe.
_NEO4J_NEXT_SEQ = """
    MERGE (m:CcfMeta {partition: $partition, key: $key})
    ON CREATE SET m.value = 0
    SET m.value = m.value + 1
    RETURN m.value AS seq
"""

_NEO4J_UPSERT_ENTITY_NODE = """
    MERGE (e:CcfEntity {partition: $partition, tenant_id: $tenant_id,
                        entity_uri: $entity_uri})
    SET e.entity_class = coalesce(e.entity_class, $entity_class),
        e.first_observed_at = CASE
            WHEN e.first_observed_at IS NULL
                 OR $observed_at < e.first_observed_at
            THEN $observed_at ELSE e.first_observed_at END,
        e.last_observed_at = CASE
            WHEN e.last_observed_at IS NULL
                 OR $observed_at > e.last_observed_at
            THEN $observed_at ELSE e.last_observed_at END
"""

_NEO4J_INSERT_ENTITY_CLAIM = """
    MERGE (c:CcfEntityClaim {partition: $partition, tenant_id: $tenant_id,
                             entity_uri: $entity_uri, claim_id: $claim_id})
    ON CREATE SET c += $props, c.seq = $seq
"""

_NEO4J_SELECT_ENTITY_CHAIN = """
    MATCH (c:CcfEntityClaim {partition: $partition, tenant_id: $tenant_id,
                             entity_uri: $entity_uri})
    RETURN c.claim_id AS claim_id, c.observed_at AS observed_at
    ORDER BY c.observed_at, c.seq
"""

_NEO4J_UPDATE_ENTITY_SUPERSESSION = """
    MATCH (c:CcfEntityClaim {partition: $partition, tenant_id: $tenant_id,
                             entity_uri: $entity_uri, claim_id: $claim_id})
    SET c.superseded_by = $superseded_by, c.superseded_at = $superseded_at
    RETURN count(c) AS matched
"""

# Two statements rather than one: the endpoint upsert and the edge upsert run
# back-to-back inside the same driver transaction, so the MATCH below always
# finds the endpoints statement one just merged (reads see own writes — the
# _GraphTxn contract). Endpoint nodes merged here without an entity claim are
# placeholders — the graph rendering of a relationships-table row whose
# subject was never upserted as an entity; a later upsert_entity_node fills
# their identity columns via coalesce.
_NEO4J_UPSERT_RELATIONSHIP_ENDPOINTS = """
    MERGE (a:CcfEntity {partition: $partition, tenant_id: $tenant_id,
                        entity_uri: $subject_uri})
    MERGE (b:CcfEntity {partition: $partition, tenant_id: $tenant_id,
                        entity_uri: $object_uri})
"""

_NEO4J_UPSERT_RELATIONSHIP_EDGE = """
    MATCH (a:CcfEntity), (b:CcfEntity)
    WHERE a.partition = $partition AND a.tenant_id = $tenant_id
      AND a.entity_uri = $subject_uri
      AND b.partition = $partition AND b.tenant_id = $tenant_id
      AND b.entity_uri = $object_uri
    MERGE (a)-[e:CCF_EDGE {partition: $partition, tenant_id: $tenant_id,
                           relationship_key: $relationship_key}]->(b)
    SET e.relationship_type = coalesce(e.relationship_type, $relationship_type),
        e.subject_uri = $subject_uri, e.object_uri = $object_uri,
        e.first_observed_at = CASE
            WHEN e.first_observed_at IS NULL
                 OR $observed_at < e.first_observed_at
            THEN $observed_at ELSE e.first_observed_at END,
        e.last_observed_at = CASE
            WHEN e.last_observed_at IS NULL
                 OR $observed_at > e.last_observed_at
            THEN $observed_at ELSE e.last_observed_at END
"""

_NEO4J_INSERT_RELATIONSHIP_CLAIM = """
    MERGE (c:CcfRelationshipClaim {partition: $partition,
                                   tenant_id: $tenant_id,
                                   relationship_key: $relationship_key,
                                   claim_id: $claim_id})
    ON CREATE SET c += $props, c.seq = $seq
"""

_NEO4J_SELECT_RELATIONSHIP_CHAIN = """
    MATCH (c:CcfRelationshipClaim {partition: $partition,
                                   tenant_id: $tenant_id,
                                   relationship_key: $relationship_key})
    RETURN c.claim_id AS claim_id, c.observed_at AS observed_at
    ORDER BY c.observed_at, c.seq
"""

_NEO4J_UPDATE_RELATIONSHIP_SUPERSESSION = """
    MATCH (c:CcfRelationshipClaim {partition: $partition,
                                   tenant_id: $tenant_id,
                                   relationship_key: $relationship_key,
                                   claim_id: $claim_id})
    SET c.superseded_by = $superseded_by, c.superseded_at = $superseded_at
    RETURN count(c) AS matched
"""

_NEO4J_INSERT_LINEAGE = """
    MERGE (l:CcfLineage {partition: $partition, tenant_id: $tenant_id,
                         claim_kind: $claim_kind, node_key: $node_key,
                         claim_id: $claim_id, lineage_id: $lineage_id})
    ON CREATE SET l.entry_json = $entry_json
"""


def _neo4j_claim_projection(claim_json: str, *, kind: str) -> dict[str, object]:
    """Write-time projections of the predicate-relevant claim fields.

    The adapter's physical model (D-IMPL-34) stores, beside the verbatim
    ``claim_json``, the fields the pushed predicates compare — so the read
    path needs no JSON parsing in Cypher:

    * ``valid_from_cmp`` / ``valid_to_cmp``: the claim's validity window
      re-rendered through :func:`ccf.contracts.canonical.canonical_timestamp`,
      so the pushed `GQ-09` cut is fixed-width canonical-text comparison
      against the canonical boundary — chronologically exact whatever offset
      the claim was authored with (`GQ-24` at
      docs/GRAPH_QUERY_SEMANTICS.md:482);
    * entity claims: ``entity_class``, plus every **string-valued** attribute
      under ``ATTRIBUTE_PROPERTY_PREFIX``. Non-string attribute values are
      deliberately not projected: ``permitted_classifications`` is a set of
      strings, so a non-string value can never satisfy the `GQ-08`
      membership test — an absent property answers NULL, NULL is never IN a
      permitted set, and the two renderings are exactly equivalent to the
      fallback's ``attributes.get(name) in classifications``;
    * relationship claims: ``relationship_type`` / ``subject_uri`` /
      ``object_uri`` — the edge triple the traverse family and the
      induced-subgraph rule (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316)
      constrain.

    ``None`` values are omitted rather than set: Cypher ``+=`` removes a
    property for a null map entry, and an absent property already reads back
    as NULL.
    """
    payload: dict[str, Any] = json.loads(claim_json)
    props: dict[str, object] = {}
    valid_from = payload.get("valid_from")
    if valid_from is not None:
        parsed_from = parse_timestamp(valid_from)
        assert parsed_from is not None  # narrowed by the None check above
        props["valid_from_cmp"] = canonical_timestamp(parsed_from)
    valid_to = payload.get("valid_to")
    if valid_to is not None:
        parsed_to = parse_timestamp(valid_to)
        assert parsed_to is not None  # narrowed by the None check above
        props["valid_to_cmp"] = canonical_timestamp(parsed_to)
    if kind == ENTITY_KIND:
        props["entity_class"] = payload["entity_class"]
        for name, value in payload.get("attributes", {}).items():
            if isinstance(value, str):
                props[ATTRIBUTE_PROPERTY_PREFIX + name] = value
    else:
        props["relationship_type"] = payload["relationship_type"]
        props["subject_uri"] = payload["subject_uri"]
        props["object_uri"] = payload["object_uri"]
    return props


class _Neo4jTxn:
    """The nine :class:`_GraphTxn` operations as parameterized Cypher.

    One open driver transaction (explicit ``begin_transaction``), so the two
    contract rules hold natively: reads inside the transaction see its own
    writes (``select_*_chain`` includes claims appended earlier in the same
    transaction), and mutating operations resolve their rowcounts before
    commit — ``MERGE … ON CREATE`` reports creation through the result
    summary's ``nodes_created`` counter, which is 1 for a new claim and 0
    for a re-arrival: the writer's idempotency signal, and for lineage the
    L-axis set-union itself (INV-CH7-17).

    Lives in this module and only this module, per the CINV-02 rule the
    module docstring states (threat T-15.2-06): no session or transaction
    construction exists in ``ccf.graph.backends.neo4j`` beyond reads.
    """

    def __init__(self, *, tx: Any, partition: str) -> None:
        self._tx = tx
        self._partition = partition

    def _run(self, statement: str, params: dict[str, object]) -> Any:
        params["partition"] = self._partition
        return self._tx.run(statement, params)

    def _created(self, statement: str, params: dict[str, object]) -> int:
        """Rows actually created — 0 for an ignored duplicate (the contract)."""
        counters = self._run(statement, params).consume().counters
        return int(counters.nodes_created)

    def _matched(self, statement: str, params: dict[str, object]) -> int:
        record = self._run(statement, params).single()
        return int(record["matched"]) if record is not None else 0

    def _next_seq(self) -> int:
        record = self._run(_NEO4J_NEXT_SEQ, {"key": "seq"}).single()
        return int(record["seq"])

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        self._run(
            _NEO4J_UPSERT_ENTITY_NODE,
            {
                "tenant_id": tenant_id,
                "entity_uri": entity_uri,
                "entity_class": entity_class,
                "observed_at": observed_at,
            },
        ).consume()
        return 1

    def insert_entity_claim(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        props = _neo4j_claim_projection(claim_json, kind=ENTITY_KIND)
        props["claim_json"] = claim_json
        props["observed_at"] = observed_at
        props["policy_bundle_version"] = policy_bundle_version
        return self._created(
            _NEO4J_INSERT_ENTITY_CLAIM,
            {
                "tenant_id": tenant_id,
                "entity_uri": entity_uri,
                "claim_id": claim_id,
                "props": props,
                "seq": self._next_seq(),
            },
        )

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        result = self._run(
            _NEO4J_SELECT_ENTITY_CHAIN,
            {"tenant_id": tenant_id, "entity_uri": entity_uri},
        )
        return [dict(record) for record in result]

    def update_entity_supersession(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        return self._matched(
            _NEO4J_UPDATE_ENTITY_SUPERSESSION,
            {
                "tenant_id": tenant_id,
                "entity_uri": entity_uri,
                "claim_id": claim_id,
                "superseded_by": superseded_by,
                "superseded_at": superseded_at,
            },
        )

    def upsert_relationship_node(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        relationship_type: str,
        subject_uri: str,
        object_uri: str,
        observed_at: str,
    ) -> int:
        self._run(
            _NEO4J_UPSERT_RELATIONSHIP_ENDPOINTS,
            {
                "tenant_id": tenant_id,
                "subject_uri": subject_uri,
                "object_uri": object_uri,
            },
        ).consume()
        self._run(
            _NEO4J_UPSERT_RELATIONSHIP_EDGE,
            {
                "tenant_id": tenant_id,
                "relationship_key": relationship_key,
                "relationship_type": relationship_type,
                "subject_uri": subject_uri,
                "object_uri": object_uri,
                "observed_at": observed_at,
            },
        ).consume()
        return 1

    def insert_relationship_claim(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        props = _neo4j_claim_projection(claim_json, kind=RELATIONSHIP_KIND)
        props["claim_json"] = claim_json
        props["observed_at"] = observed_at
        props["policy_bundle_version"] = policy_bundle_version
        return self._created(
            _NEO4J_INSERT_RELATIONSHIP_CLAIM,
            {
                "tenant_id": tenant_id,
                "relationship_key": relationship_key,
                "claim_id": claim_id,
                "props": props,
                "seq": self._next_seq(),
            },
        )

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        result = self._run(
            _NEO4J_SELECT_RELATIONSHIP_CHAIN,
            {"tenant_id": tenant_id, "relationship_key": relationship_key},
        )
        return [dict(record) for record in result]

    def update_relationship_supersession(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        return self._matched(
            _NEO4J_UPDATE_RELATIONSHIP_SUPERSESSION,
            {
                "tenant_id": tenant_id,
                "relationship_key": relationship_key,
                "claim_id": claim_id,
                "superseded_by": superseded_by,
                "superseded_at": superseded_at,
            },
        )

    def insert_lineage(
        self,
        *,
        tenant_id: str,
        claim_kind: str,
        node_key: str,
        claim_id: str,
        lineage_id: str,
        entry_json: str,
    ) -> int:
        return self._created(
            _NEO4J_INSERT_LINEAGE,
            {
                "tenant_id": tenant_id,
                "claim_kind": claim_kind,
                "node_key": node_key,
                "claim_id": claim_id,
                "lineage_id": lineage_id,
                "entry_json": entry_json,
            },
        )


class Neo4jGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one Neo4j graph — extras-gated (plan 15.2-12).

    Same algorithm as every other writer, inherited rather than restated.
    What differs is the transaction: :class:`_Neo4jTxn` implements the nine
    typed operations as parameterized Cypher over one explicit driver
    transaction — no SQL ``ClassVar`` statements are set here, exactly as
    the memory backend (the typed seam's second non-SQL implementation).
    All-or-nothing comes from the driver transaction: commit on success,
    rollback on exception.
    """

    def __init__(self, *, store: Neo4jGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        with self._store.session() as session:
            tx = session.begin_transaction()
            try:
                yield _Neo4jTxn(tx=tx, partition=self._store.partition)
            except BaseException:
                tx.rollback()
                raise
            else:
                tx.commit()


# --- the MongoDB write path (plan 15.2-13) ------------------------------------
#
# The nine typed operations as **buffered pymongo bulk operations**, confined
# to this module per the CINV-02 rule the module docstring states: the typed
# operation seam is part of the write path, and write code outside this module
# is write code outside the guard (threat T-15.2-06). Nothing here is text:
# every operation is a filter document plus an update document assembled from
# typed values, so the "no SQL from f-strings" rule holds vacuously and the
# T-15.2-01 surface reduces to the one field-path site
# (``ccf.graph.backends.mongo.attribute_field_path``).
#
# **Why buffered.** A plain ``mongo:7`` deployment is a standalone server, and
# MongoDB's multi-document transactions require a replica set or a sharded
# cluster — which a GitHub Actions service container cannot be asked to start
# (a service block cannot pass ``--replSet``). Rather than make the adapter's
# conformance depend on a topology, ``_MongoTxn`` is the **batched adapter**
# the ``_GraphTxn`` contract already anticipates in as many words (D-IMPL-88,
# the Protocol docstring above): mutating operations resolve their rowcounts
# before commit from committed state read before buffering plus the buffer's
# own contents — sound because INV-CH7-10 guarantees no concurrent writer can
# invalidate the pre-commit read — and reads see the buffer. All-or-nothing on
# the failure path is exact: a raised exception drops the buffer, and nothing
# was applied.
#
# The honest residual, stated rather than implied: a failure *during* the flush
# can leave a partially applied write, exactly as the module docstring's
# single-writer claim is bounded at "no unforced path exists". Every operation
# is an upsert on its compound identity, so re-running the same admission
# converges — the writer's whole algorithm is idempotent by construction
# (INV-CH7-04), which is what makes a retry the correct response rather than a
# repair.


def _mongo_claim_projection(claim_json: str, *, kind: str) -> dict[str, object]:
    """Write-time projections of the predicate-relevant claim fields.

    The MongoDB twin of :func:`_neo4j_claim_projection`, and the same
    D-IMPL-34 argument: the adapter's physical model stores, beside the
    verbatim ``claim_json``, the fields the pushed predicates compare — so the
    read path needs no JSON parsing inside an aggregation stage.

    * ``valid_from_cmp`` / ``valid_to_cmp``: the claim's validity window
      re-rendered through :func:`ccf.contracts.canonical.canonical_timestamp`,
      so the pushed `GQ-09` cut is fixed-width canonical-text comparison
      against the canonical boundary — chronologically exact whatever offset
      the claim was authored with (`GQ-24` at
      docs/GRAPH_QUERY_SEMANTICS.md:482);
    * entity claims: ``entity_class``, plus every **string-valued** attribute
      whose name :func:`~ccf.graph.backends.mongo.attribute_field_path` admits
      as a field path. Two exclusions, both deliberate and both harmless:
      non-string values can never satisfy the `GQ-08` membership test against
      a set of strings, and an unsafe attribute name is not made into document
      structure at all (threat T-15.2-01). In both cases the attribute is
      still carried verbatim inside ``claim_json``, an absent field matches no
      ``$in`` over strings, and the read side declines the pushdown for an
      unsafe name — so the answer is the fallback's, byte-identical (D-04);
    * relationship claims: ``relationship_type`` / ``subject_uri`` /
      ``object_uri`` — the edge triple the traverse family and the
      induced-subgraph rule (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316)
      constrain.

    ``None`` values are omitted rather than stored: an absent field already
    reads back as null, and the read path's ``{"field": None}`` clause matches
    an absent field and an explicit null alike.
    """
    payload: dict[str, Any] = json.loads(claim_json)
    fields: dict[str, object] = {}
    valid_from = payload.get("valid_from")
    if valid_from is not None:
        parsed_from = parse_timestamp(valid_from)
        assert parsed_from is not None  # narrowed by the None check above
        fields["valid_from_cmp"] = canonical_timestamp(parsed_from)
    valid_to = payload.get("valid_to")
    if valid_to is not None:
        parsed_to = parse_timestamp(valid_to)
        assert parsed_to is not None  # narrowed by the None check above
        fields["valid_to_cmp"] = canonical_timestamp(parsed_to)
    if kind == ENTITY_KIND:
        fields["entity_class"] = payload["entity_class"]
        for name, value in payload.get("attributes", {}).items():
            path = attribute_field_path(name)
            if path is not None and isinstance(value, str):
                fields[path] = value
    else:
        fields["relationship_type"] = payload["relationship_type"]
        fields["subject_uri"] = payload["subject_uri"]
        fields["object_uri"] = payload["object_uri"]
    return fields


class _MongoTxn:
    """The nine :class:`_GraphTxn` operations as buffered pymongo bulk writes.

    The batched-adapter shape the Protocol contract names (D-IMPL-88): every
    mutation is appended to a per-collection ordered operation list and
    nothing reaches the server until :meth:`commit`. Both contract rules hold:

    * **Rowcounts resolve before commit.** ``insert_*_claim`` returns 0 for a
      re-arrival of a claim id already held — committed or buffered — which is
      the writer's idempotency signal, and ``insert_lineage`` returns 0 on a
      full-entry-identity collision, which *is* the L-axis set-union
      (INV-CH7-17). Single-writer (INV-CH7-10) is what makes the pre-buffer
      read authoritative.
    * **Reads see this transaction's own operations.**
      ``select_*_chain`` merges the committed chain with the claim appended
      earlier in the same transaction, and a supersession set earlier in the
      transaction is applied to the buffered document too.

    Ordering inside a collection is preserved by ``bulk_write(ordered=True)``,
    which is what lets the chain restitch update a claim this same transaction
    inserted. Ordering *between* collections carries no meaning — the five
    identities are independent.

    Lives in this module and only this module, per the CINV-02 rule the module
    docstring states (threat T-15.2-06): no write operation exists in
    ``ccf.graph.backends.mongo``.
    """

    def __init__(self, *, store: MongoGraphStore) -> None:
        from pymongo import UpdateOne  # noqa: PLC0415 - lazy; the extra gates it

        self._update_one = UpdateOne
        self._store = store
        self._ops: dict[str, list[Any]] = {}
        self._entity_claims: list[dict[str, Any]] = []
        self._relationship_claims: list[dict[str, Any]] = []
        self._lineage: set[tuple[str, ...]] = set()

    # -- buffer mechanics ----------------------------------------------------

    def _buffer(
        self,
        collection: str,
        identity: dict[str, Any],
        update: dict[str, Any],
        *,
        upsert: bool,
    ) -> None:
        self._ops.setdefault(collection, []).append(
            self._update_one(identity, update, upsert=upsert)
        )

    def _insert_once(
        self, collection: str, identity: dict[str, Any], document: dict[str, Any]
    ) -> None:
        """Buffer an ignore-on-conflict insert of ``document`` at ``identity``.

        ``$setOnInsert`` under an upsert *is* ``ON CONFLICT DO NOTHING`` /
        ``MERGE … ON CREATE``: a document already at this identity is left
        exactly as it stands. The identity fields are supplied by the filter
        and deliberately excluded from the update document, so no single field
        is written by two paths of the same operation.
        """
        payload = {
            field: value
            for field, value in document.items()
            if field not in identity
        }
        self._buffer(collection, identity, {"$setOnInsert": payload}, upsert=True)

    def _held(self, collection: str, identity: dict[str, Any]) -> bool:
        """Is a document already committed at this identity?"""
        return (
            self._store.collection(collection).find_one(identity, {"_id": True})
            is not None
        )

    def _arrival_index(self, collection: str, node_filter: dict[str, Any]) -> int:
        """Position of the next claim in one node's arrival order.

        The document rendering of SQLite's ``rowid`` / Postgres's
        ``BIGSERIAL`` in the one role the read path uses it for: the tiebreak
        that keeps a node's claim chain totally ordered when two claims share
        an ``observed_at`` (``ORDER BY observed_at, rowid``). It is **per
        node**, not global, because that is the whole of what the tiebreak
        means — which also removes the need for a counter collection and for
        the counter's rollback gap. Single-writer (INV-CH7-10) makes the count
        authoritative.
        """
        return int(self._store.collection(collection).count_documents(node_filter))

    def commit(self) -> None:
        """Apply the buffer, one ordered bulk write per collection."""
        for collection, operations in self._ops.items():
            if operations:
                self._store.collection(collection).bulk_write(
                    operations, ordered=True
                )
        self._ops.clear()

    def rollback(self) -> None:
        """Drop the buffer. Nothing was applied, so nothing is undone."""
        self._ops.clear()

    # -- the nine typed operations -------------------------------------------

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        identity = {**self._store.scope(tenant_id), "entity_uri": entity_uri}
        # `$min` / `$max` widen the observed window and set the field on
        # insert; canonical text compares lexicographically as
        # chronologically, so they render MIN()/MAX() exactly.
        self._buffer(
            ENTITY_NODES,
            identity,
            {
                "$setOnInsert": {"entity_class": entity_class},
                "$min": {"first_observed_at": observed_at},
                "$max": {"last_observed_at": observed_at},
            },
            upsert=True,
        )
        return 1

    def insert_entity_claim(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        identity = {**scope, "entity_uri": entity_uri, "claim_id": claim_id}
        buffered = {row["claim_id"] for row in self._entity_claims}
        if claim_id in buffered or self._held(ENTITY_CLAIMS, identity):
            return 0
        document: dict[str, Any] = {
            **identity,
            "claim_json": claim_json,
            "observed_at": observed_at,
            "policy_bundle_version": policy_bundle_version,
            "superseded_by": None,
            "superseded_at": None,
            "seq": self._arrival_index(
                ENTITY_CLAIMS, {**scope, "entity_uri": entity_uri}
            )
            + len(self._entity_claims),
            **_mongo_claim_projection(claim_json, kind=ENTITY_KIND),
        }
        self._entity_claims.append(document)
        self._insert_once(ENTITY_CLAIMS, identity, document)
        return 1

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        scope = self._store.scope(tenant_id)
        committed = self._store.collection(ENTITY_CLAIMS).find(
            {**scope, "entity_uri": entity_uri},
            {"_id": False, "claim_id": True, "observed_at": True, "seq": True},
        )
        rows: list[dict[str, Any]] = [dict(row) for row in committed]
        rows += [
            {
                "claim_id": row["claim_id"],
                "observed_at": row["observed_at"],
                "seq": row["seq"],
            }
            for row in self._entity_claims
            if row["entity_uri"] == entity_uri
        ]
        # Stable sort on (observed_at, seq) — the document rendering of
        # `ORDER BY observed_at, rowid`.
        rows.sort(key=lambda row: (row["observed_at"], row["seq"]))
        return rows

    def update_entity_supersession(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        identity = {
            **self._store.scope(tenant_id),
            "entity_uri": entity_uri,
            "claim_id": claim_id,
        }
        matched = 0
        for row in self._entity_claims:
            if row["claim_id"] == claim_id and row["entity_uri"] == entity_uri:
                row["superseded_by"] = superseded_by
                row["superseded_at"] = superseded_at
                matched = 1
        if matched == 0 and self._held(ENTITY_CLAIMS, identity):
            matched = 1
        self._buffer(
            ENTITY_CLAIMS,
            identity,
            {
                "$set": {
                    "superseded_by": superseded_by,
                    "superseded_at": superseded_at,
                }
            },
            upsert=False,
        )
        return matched

    def upsert_relationship_node(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        relationship_type: str,
        subject_uri: str,
        object_uri: str,
        observed_at: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        self._buffer(
            RELATIONSHIP_NODES,
            {**scope, "relationship_key": relationship_key},
            {
                "$setOnInsert": {
                    "relationship_type": relationship_type,
                    "subject_uri": subject_uri,
                    "object_uri": object_uri,
                },
                "$min": {"first_observed_at": observed_at},
                "$max": {"last_observed_at": observed_at},
            },
            upsert=True,
        )
        # The doubled-edge traversal layout (15.2-RESEARCH.md Pitfall 3):
        # `$graphLookup` follows connectFromField -> connectToField in ONE
        # direction, and CCF traversal is undirected (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201), so each edge is stored forward
        # AND reverse and one lookup expresses the undirected walk. The two
        # documents are maintained here, in the same buffered transaction as
        # the node they double — the layout cannot drift from the edge it
        # represents. Crossability is decided by the read path against the
        # surviving relationship claims, so these documents carry identity and
        # endpoints only; they never carry admissibility.
        for direction, source, target in (
            ("forward", subject_uri, object_uri),
            ("reverse", object_uri, subject_uri),
        ):
            self._buffer(
                TRAVERSAL_EDGES,
                {
                    **scope,
                    "relationship_key": relationship_key,
                    "direction": direction,
                },
                {
                    "$setOnInsert": {
                        "from": source,
                        "to": target,
                        "relationship_type": relationship_type,
                    }
                },
                upsert=True,
            )
        return 1

    def insert_relationship_claim(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        identity = {
            **scope,
            "relationship_key": relationship_key,
            "claim_id": claim_id,
        }
        buffered = {row["claim_id"] for row in self._relationship_claims}
        if claim_id in buffered or self._held(RELATIONSHIP_CLAIMS, identity):
            return 0
        document: dict[str, Any] = {
            **identity,
            "claim_json": claim_json,
            "observed_at": observed_at,
            "policy_bundle_version": policy_bundle_version,
            "superseded_by": None,
            "superseded_at": None,
            "seq": self._arrival_index(
                RELATIONSHIP_CLAIMS,
                {**scope, "relationship_key": relationship_key},
            )
            + len(self._relationship_claims),
            **_mongo_claim_projection(claim_json, kind=RELATIONSHIP_KIND),
        }
        self._relationship_claims.append(document)
        self._insert_once(RELATIONSHIP_CLAIMS, identity, document)
        return 1

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        scope = self._store.scope(tenant_id)
        committed = self._store.collection(RELATIONSHIP_CLAIMS).find(
            {**scope, "relationship_key": relationship_key},
            {"_id": False, "claim_id": True, "observed_at": True, "seq": True},
        )
        rows: list[dict[str, Any]] = [dict(row) for row in committed]
        rows += [
            {
                "claim_id": row["claim_id"],
                "observed_at": row["observed_at"],
                "seq": row["seq"],
            }
            for row in self._relationship_claims
            if row["relationship_key"] == relationship_key
        ]
        rows.sort(key=lambda row: (row["observed_at"], row["seq"]))
        return rows

    def update_relationship_supersession(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        identity = {
            **self._store.scope(tenant_id),
            "relationship_key": relationship_key,
            "claim_id": claim_id,
        }
        matched = 0
        for row in self._relationship_claims:
            if (
                row["claim_id"] == claim_id
                and row["relationship_key"] == relationship_key
            ):
                row["superseded_by"] = superseded_by
                row["superseded_at"] = superseded_at
                matched = 1
        if matched == 0 and self._held(RELATIONSHIP_CLAIMS, identity):
            matched = 1
        self._buffer(
            RELATIONSHIP_CLAIMS,
            identity,
            {
                "$set": {
                    "superseded_by": superseded_by,
                    "superseded_at": superseded_at,
                }
            },
            upsert=False,
        )
        return matched

    def insert_lineage(
        self,
        *,
        tenant_id: str,
        claim_kind: str,
        node_key: str,
        claim_id: str,
        lineage_id: str,
        entry_json: str,
    ) -> int:
        identity = {
            **self._store.scope(tenant_id),
            "claim_kind": claim_kind,
            "node_key": node_key,
            "claim_id": claim_id,
            "lineage_id": lineage_id,
        }
        fingerprint = (tenant_id, claim_kind, node_key, claim_id, lineage_id)
        if fingerprint in self._lineage or self._held(LINEAGE, identity):
            return 0
        self._lineage.add(fingerprint)
        self._insert_once(LINEAGE, identity, {**identity, "entry_json": entry_json})
        return 1


class MongoGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one MongoDB graph — extras-gated (plan 15.2-13).

    Same algorithm as every other writer, inherited rather than restated. What
    differs is the transaction: :class:`_MongoTxn` implements the nine typed
    operations as buffered pymongo bulk operations — no SQL ``ClassVar``
    statements are set here, exactly as the memory and Neo4j backends (the
    typed seam's third non-SQL implementation, and its first *batched* one).
    All-or-nothing on the failure path comes from the buffer: an exception
    drops it, and nothing was applied.
    """

    def __init__(self, *, store: MongoGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        txn = _MongoTxn(store=self._store)
        try:
            yield txn
        except BaseException:
            txn.rollback()
            raise
        else:
            txn.commit()


# --- the Fluree v4 write path (plan 15.3-02) ---------------------------------
#
# The nine typed operations as one buffered JSON-LD batch. Every statement
# below is a committed-state read: the batch itself carries no `where` clause,
# because read-before-buffer plus INV-CH7-10 single-writer resolves every
# conditional in Python before the body is built (D-01/D-02, and see
# `_FlureeTxn.commit`).
#
# Statement text is code-authored in full — no identifier interpolation exists
# in this module — and every value binds as a request parameter.

_FLUREE_ENTITY_WINDOW = """
    MATCH (n:CcfEntity {ccf_partition: $partition, ccf_tenant_id: $tenant,
                        ccf_entity_uri: $key})
    RETURN n.ccf_first_observed_at AS first_observed_at,
           n.ccf_last_observed_at AS last_observed_at
"""

_FLUREE_EDGE_WINDOW = """
    MATCH (n:CcfEdge {ccf_partition: $partition, ccf_tenant_id: $tenant,
                      ccf_relationship_key: $key})
    RETURN n.ccf_first_observed_at AS first_observed_at,
           n.ccf_last_observed_at AS last_observed_at
"""

#: Serves both the boolean "is this claim committed?" question and the
#: supersession values a ground delete needs — one round trip, two answers.
_FLUREE_ENTITY_CLAIM = """
    MATCH (c:CcfEntityClaim {ccf_partition: $partition, ccf_tenant_id: $tenant,
                             ccf_entity_uri: $key, ccf_claim_id: $claim})
    RETURN c.ccf_superseded_by AS superseded_by,
           c.ccf_superseded_at AS superseded_at
"""

_FLUREE_RELATIONSHIP_CLAIM = """
    MATCH (c:CcfRelationshipClaim {ccf_partition: $partition,
                                   ccf_tenant_id: $tenant,
                                   ccf_relationship_key: $key,
                                   ccf_claim_id: $claim})
    RETURN c.ccf_superseded_by AS superseded_by,
           c.ccf_superseded_at AS superseded_at
"""

_FLUREE_ENTITY_CHAIN = """
    MATCH (c:CcfEntityClaim {ccf_partition: $partition, ccf_tenant_id: $tenant,
                             ccf_entity_uri: $key})
    RETURN c.ccf_claim_id AS claim_id, c.ccf_observed_at AS observed_at,
           c.ccf_seq AS seq
    ORDER BY c.ccf_observed_at, c.ccf_seq
"""

_FLUREE_RELATIONSHIP_CHAIN = """
    MATCH (c:CcfRelationshipClaim {ccf_partition: $partition,
                                   ccf_tenant_id: $tenant,
                                   ccf_relationship_key: $key})
    RETURN c.ccf_claim_id AS claim_id, c.ccf_observed_at AS observed_at,
           c.ccf_seq AS seq
    ORDER BY c.ccf_observed_at, c.ccf_seq
"""

_FLUREE_ENTITY_CLAIM_COUNT = """
    MATCH (c:CcfEntityClaim {ccf_partition: $partition, ccf_tenant_id: $tenant,
                             ccf_entity_uri: $key})
    RETURN count(c) AS n
"""

_FLUREE_RELATIONSHIP_CLAIM_COUNT = """
    MATCH (c:CcfRelationshipClaim {ccf_partition: $partition,
                                   ccf_tenant_id: $tenant,
                                   ccf_relationship_key: $key})
    RETURN count(c) AS n
"""

_FLUREE_LINEAGE_COUNT = """
    MATCH (l:CcfLineage {ccf_partition: $partition, ccf_tenant_id: $tenant,
                         ccf_claim_kind: $kind, ccf_node_key: $node,
                         ccf_claim_id: $claim, ccf_lineage_id: $lineage})
    RETURN count(l) AS n
"""

#: Separator inside a materialized policy key. Code-authored, and impossible in
#: a CCF class or attribute name, so no artifact-authored string can forge a
#: key boundary — the near-miss discrimination probe F-A6 asserted directly.
_POLICY_KEY_SEPARATOR = "\x00"

#: The five node kinds `_mint_id` addresses. Short, code-authored, and part of
#: the hashed identity, so two node classes sharing an identity tuple still
#: mint distinct `@id`s.
_FLUREE_ENTITY = "e"
_FLUREE_ENTITY_CLAIM_KIND = "ec"
_FLUREE_EDGE = "r"
_FLUREE_RELATIONSHIP_CLAIM_KIND = "rc"
_FLUREE_LINEAGE = "l"

#: Namespace prefixes on :data:`P_ADMIT_KEY`. These are what make the entity
#: and relationship admissibility namespaces disjoint, so an ``entity_uri`` can
#: never collide with a ``relationship_key`` inside the walk's single
#: ``$admissible`` parameter list (15.3-RESEARCH.md §R5).
_ENTITY_ADMIT_PREFIX = "e:"
_RELATIONSHIP_ADMIT_PREFIX = "r:"


def _fluree_claim_projection(claim_json: str, *, kind: str) -> dict[str, object]:
    """Write-time projections of the predicate-relevant claim fields.

    The Fluree twin of :func:`_mongo_claim_projection` and
    :func:`_neo4j_claim_projection`, and the same D-IMPL-34 argument: the
    adapter's physical model stores, beside the verbatim ``claim_json``, the
    fields the pushed predicates compare — so the read path needs no JSON
    parsing inside a query.

    **This is the DI-15.2-03 non-reintroduction site (§R8 vector 1), and it
    carries a burden its two twins do not.** ``valid_from`` / ``valid_to`` are
    re-rendered through :func:`~ccf.graph.reader.parse_timestamp` →
    :func:`~ccf.contracts.canonical.canonical_timestamp` into
    :data:`P_VALID_FROM_CMP` / :data:`P_VALID_TO_CMP`, and the payload's raw
    JSON value is **never** copied as a shortcut. The SQL adapters can afford a
    second chance because they re-normalize at read time via
    ``_utc_fixed_width``; **Fluree has no read-time equivalent.** The
    normalization happens here, in Python, at write time, and if it is skipped
    there is nowhere left to recover it — an offset-authored claim would
    compare as raw text against a canonical boundary and silently drop out of
    every pushed answer while the fallback kept including it (D-IMPL-90's
    original defect, re-entering through a different door).

    * entity claims: ``entity_class``, the multi-valued policy key below, and
      every **string-valued** attribute whose name
      :func:`~ccf.graph.backends.fluree.attribute_predicate` admits as a
      predicate. Both exclusions are harmless: a non-string value can never
      satisfy the `GQ-08` membership test against a set of strings (assumption
      A10), and an unsafe name is not made into an IRI at all — the attribute
      still travels verbatim inside ``claim_json`` and still contributes its
      policy key;
    * relationship claims: ``relationship_type`` / ``subject_uri`` /
      ``object_uri`` — the edge triple the traverse family and the
      induced-subgraph rule (`GQ-16` at
      docs/GRAPH_QUERY_SEMANTICS.md:316) constrain.

    **The multi-valued policy key (probe F-A6, D-07 rung 1).** Neo4j pushes
    `GQ-08`'s classification cut with dynamic property access
    ``c[$attribute_by_class[ec]]``. On this engine that expression **parses,
    returns 200 and evaluates to null** — it fails *silently*, so porting
    ``_ENTITY_POLICY`` would have produced a policy family excluding every
    claim while reporting success on the predicate family that gates the
    majority of real queries. The resolution materializes the cut instead: one
    value ``"{entity_class}\\0{attr_name}\\0{attr_value}"`` per string-valued
    attribute, pushed as ``c.ccf_policy_key IN $keys`` with ``RETURN DISTINCT``
    — semantically identical because a multi-valued property fans out into one
    row per value rather than yielding a list.

    That materialization is exactly `GQ-08`'s three cuts as pure membership: a
    class with no declared attribute contributes no key and is inadmissible; a
    claim carrying no value for its class's attribute produces no matching key
    and is inadmissible; and **no artifact-authored string ever enters query
    text** — the keys travel as a parameter list and the stored keys are
    literal values.

    ``None`` values are omitted rather than stored: on RDF an absent property
    already reads back as null, and writing an explicit null would create a
    value where the read path's ``IS NULL`` expects none.
    """
    payload: dict[str, Any] = json.loads(claim_json)
    fields: dict[str, object] = {}
    valid_from = payload.get("valid_from")
    if valid_from is not None:
        parsed_from = parse_timestamp(valid_from)
        assert parsed_from is not None  # narrowed by the None check above
        fields[P_VALID_FROM_CMP] = canonical_timestamp(parsed_from)
    valid_to = payload.get("valid_to")
    if valid_to is not None:
        parsed_to = parse_timestamp(valid_to)
        assert parsed_to is not None  # narrowed by the None check above
        fields[P_VALID_TO_CMP] = canonical_timestamp(parsed_to)
    if kind == ENTITY_KIND:
        entity_class = payload["entity_class"]
        fields[P_ENTITY_CLASS] = entity_class
        policy_keys: list[str] = []
        for name, value in payload.get("attributes", {}).items():
            if not isinstance(value, str):
                continue
            policy_keys.append(
                _POLICY_KEY_SEPARATOR.join((entity_class, name, value))
            )
            predicate = attribute_predicate(name)
            if predicate is not None:
                fields[predicate] = value
        if policy_keys:
            # Sorted so the rendered body is a deterministic function of the
            # claim, exactly as the Mongo filter renderings are.
            fields[P_POLICY_KEY] = sorted(policy_keys)
    else:
        fields[P_RELATIONSHIP_TYPE] = payload["relationship_type"]
        fields[P_SUBJECT_URI] = payload["subject_uri"]
        fields[P_OBJECT_URI] = payload["object_uri"]
    return fields


class _FlureeTxn:
    """The nine :class:`_GraphTxn` operations as one buffered JSON-LD batch.

    The batched-adapter shape the Protocol contract names (D-IMPL-88) in its
    purest form: every mutation is appended to a ground-triple accumulator and
    **nothing reaches the server until** :meth:`commit`, which issues exactly
    one ``POST``. Both contract rules hold:

    * **Rowcounts resolve before commit.** ``insert_*_claim`` returns 0 for a
      re-arrival of a claim id already held — committed or buffered — which is
      the writer's idempotency signal, and ``insert_lineage`` returns 0 on a
      full-entry-identity collision, which *is* the L-axis set-union
      (INV-CH7-17). Single-writer (INV-CH7-10) is what makes the pre-buffer
      read authoritative.
    * **Reads see this transaction's own operations.** ``select_*_chain``
      merges the committed chain with claims appended earlier in the same
      transaction, and a supersession set earlier in the transaction is applied
      to the buffered triple too — by mutating it, since it has not been sent.

    **The commit body carries no guard clause, and that is a ruling rather than
    a preference.** A JSON-LD update body carries one ``where``, one ``delete``
    and one ``insert``; independent conditionals would *join* rather than
    union, and a body mixing a guarded update with unrelated ground inserts
    **silently drops the inserts whenever the guard misses** — the documented
    trap. Probe F-A4(a) established that a ground ``delete`` with no ``where``
    is accepted and applied, and its positive control established that the
    probe had discriminating power (without the ``delete``, both values
    survive). **Dave ruled `approved` on 2026-08-08**: D-02's letter holds
    unchanged and the SPARQL UPDATE multi-operation departure is not taken.

    **``opts.eventTime`` is never set.** Backdated commits look like the answer
    to CCF's bitemporality and are not (Pitfall 12): they require monotonically
    non-decreasing RFC 3339 values along the commit chain, and L2's write
    stream guarantees none — ``observed_at`` is data, arbitrary and frequently
    late-arriving. Tying it to Fluree's commit clock is the
    transaction-time-for-observation-time substitution D-IMPL-88 forbids. A
    future reader who discovers the feature should find the refusal already
    argued here.

    **``flakes_added`` cannot implement the per-operation rowcount contract,
    and on this build does not exist.** The contract requires a rowcount *per
    operation* while one POST yields at most one aggregate receipt, so a
    receipt field could only ever have cross-checked the sum. Probe F-A4(d)
    then measured that ``fluree/server:4.1.4`` returns no ``flakes_added`` at
    all (nor ``flakes_retracted``, ``previous_commit_id`` or ``timestamp``) —
    the documented receipt shape is not what this build sends. So no
    cross-check is written: there is nothing to cross-check against, and the
    read-before-buffer mechanism was always the authority.

    Ordering inside the body carries no meaning beyond ``delete`` preceding
    ``insert``: the five identities are independent and every operation is an
    assertion about its own subject.

    Lives in this module and only this module, per the CINV-02 rule the module
    docstring states (threat T-15.2-06): **no write operation exists in
    ``ccf.graph.backends.fluree``.**
    """

    def __init__(self, *, store: FlureeGraphStore) -> None:
        self._store = store
        self._insert: list[dict[str, Any]] = []
        self._delete: list[dict[str, Any]] = []
        self._entity_claims: list[dict[str, Any]] = []
        self._relationship_claims: list[dict[str, Any]] = []
        self._lineage: set[tuple[str, ...]] = set()
        # Node id -> the observed window currently in effect (committed or
        # buffered). Populated lazily by one read per node per transaction.
        self._windows: dict[str, tuple[str, str]] = {}
        # Node id -> the pending insert document for a node this transaction
        # created. Nothing in here has been sent, so widening it is a mutation
        # rather than a delete/insert pair.
        self._pending: dict[str, dict[str, Any]] = {}

    # -- buffer mechanics ----------------------------------------------------

    def _replace(
        self,
        node_id: str,
        predicate: str,
        old: object | None,
        new: object | None,
    ) -> None:
        """Retract one committed value and assert its replacement.

        The ground delete + ground insert pair F-A4(a) proved and Dave ruled
        `approved`. It exists because JSON-LD offers no ``$set`` analog: RDF
        set semantics means asserting a second value **adds** it beside the
        first rather than overwriting, so a supersession update must know the
        old value in order to retract it. This is the one operation where
        :class:`_MongoTxn` is not a complete template — the rowcount half
        carries verbatim, this mutation half is new.

        A no-op replacement emits nothing: ``_restitch_chain`` re-states every
        link of a chain on every write, so identical-value calls are the common
        case rather than the exception.
        """
        if old == new:
            return
        if old is not None:
            self._delete.append({"@id": node_id, predicate: old})
        if new is not None:
            self._insert.append({"@id": node_id, predicate: new})

    def _rows(self, statement: str, params: dict[str, object]) -> list[dict[str, Any]]:
        """One committed-state read."""
        return self._store.post_query(statement, params)

    def _count(self, statement: str, params: dict[str, object]) -> int:
        """One committed-state ``count()`` read."""
        rows = self._rows(statement, params)
        return int(rows[0]["n"]) if rows else 0

    def _upsert_node(
        self,
        *,
        node_id: str,
        window_statement: str,
        window_params: dict[str, object],
        document: dict[str, Any],
        observed_at: str,
    ) -> int:
        """Create the node on first sight, widen its observed window after.

        ``first_observed_at`` only ever moves earlier and ``last_observed_at``
        only ever moves later; nothing is deleted. Canonical text compares
        lexicographically as chronologically, so ``min`` / ``max`` over the
        stored strings render ``MIN()`` / ``MAX()`` exactly.

        The widening is a delete/insert pair rather than an overwrite for the
        same reason supersession is (:meth:`_replace`): a bare second assertion
        would leave the node carrying *two* ``first_observed_at`` values, and
        RDF's fan-out would then surface both.
        """
        window = self._windows.get(node_id)
        if window is None:
            committed = self._rows(window_statement, window_params)
            if not committed:
                self._insert.append(document)
                self._pending[node_id] = document
                self._windows[node_id] = (observed_at, observed_at)
                return 1
            window = (
                str(committed[0]["first_observed_at"]),
                str(committed[0]["last_observed_at"]),
            )
        first = min(window[0], observed_at)
        last = max(window[1], observed_at)
        if (first, last) != window:
            pending = self._pending.get(node_id)
            if pending is not None:
                pending[P_FIRST_OBSERVED_AT] = first
                pending[P_LAST_OBSERVED_AT] = last
            else:
                self._replace(node_id, P_FIRST_OBSERVED_AT, window[0], first)
                self._replace(node_id, P_LAST_OBSERVED_AT, window[1], last)
        self._windows[node_id] = (first, last)
        return 1

    @staticmethod
    def _apply_supersession(
        document: dict[str, Any],
        *,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> None:
        """Set or clear supersession on a triple that has not been sent yet.

        Clearing **removes** the key rather than writing null: on RDF an absent
        property already reads back as null, and an explicit null would create
        a value where the read path's ``IS NULL`` expects none.
        """
        for predicate, value in (
            (P_SUPERSEDED_BY, superseded_by),
            (P_SUPERSEDED_AT, superseded_at),
        ):
            if value is None:
                document.pop(predicate, None)
            else:
                document[predicate] = value

    def commit(self) -> None:
        """Apply the whole buffer as ONE ground JSON-LD transaction."""
        if self._insert or self._delete:
            body: dict[str, object] = {"@context": ADAPTER_CONTEXT}
            if self._delete:
                body["delete"] = list(self._delete)
            if self._insert:
                body["insert"] = list(self._insert)
            self._store.post_update(body)
        self.rollback()

    def rollback(self) -> None:
        """Drop the buffer. Nothing was applied, so nothing is undone."""
        self._insert.clear()
        self._delete.clear()
        self._entity_claims.clear()
        self._relationship_claims.clear()
        self._lineage.clear()
        self._windows.clear()
        self._pending.clear()

    # -- the nine typed operations -------------------------------------------

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        node_id = _mint_id(_FLUREE_ENTITY, partition, tenant_id, entity_uri)
        return self._upsert_node(
            node_id=node_id,
            window_statement=_FLUREE_ENTITY_WINDOW,
            window_params={**scope, "key": entity_uri},
            document={
                "@id": node_id,
                "@type": L_ENTITY,
                P_PARTITION: partition,
                P_TENANT: tenant_id,
                P_ENTITY_URI: entity_uri,
                P_ENTITY_CLASS: entity_class,
                # The `e:` prefix is what keeps the entity and relationship
                # admissibility namespaces disjoint, so an `entity_uri` can
                # never collide with a `relationship_key` in the walk's one
                # `$admissible` parameter list.
                P_ADMIT_KEY: _ENTITY_ADMIT_PREFIX + entity_uri,
                P_FIRST_OBSERVED_AT: observed_at,
                P_LAST_OBSERVED_AT: observed_at,
            },
            observed_at=observed_at,
        )

    def insert_entity_claim(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        buffered = {row[P_CLAIM_ID] for row in self._entity_claims}
        if claim_id in buffered:
            return 0
        identity: dict[str, object] = {
            **scope,
            "key": entity_uri,
            "claim": claim_id,
        }
        if self._rows(_FLUREE_ENTITY_CLAIM, identity):
            return 0
        node_id = _mint_id(
            _FLUREE_ENTITY_CLAIM_KIND, partition, tenant_id, entity_uri, claim_id
        )
        document: dict[str, Any] = {
            "@id": node_id,
            "@type": L_ENTITY_CLAIM,
            P_PARTITION: partition,
            P_TENANT: tenant_id,
            P_ENTITY_URI: entity_uri,
            P_CLAIM_ID: claim_id,
            P_CLAIM_JSON: claim_json,
            P_OBSERVED_AT: observed_at,
            P_POLICY_VERSION: policy_bundle_version,
            # Committed count for THIS entity plus this transaction's own
            # buffered claims for THIS entity. Both terms must be scoped to
            # the same key or the sum is not a sequence: an unscoped
            # `len(self._entity_claims)` would count claims buffered for
            # OTHER entities, so `A1, B1, A2` in one transaction gives `A`
            # seq 0 and 2, and the next transaction's `A3` reads
            # `count(A) == 2` and computes 2 — a duplicate. Two claims of one
            # entity sharing an `observed_at` and a `seq` then order
            # non-deterministically under `ORDER BY observed_at, seq`, and
            # `_restitch_chain` yields a different supersession chain per
            # read. Dormant while `BaseGraphWriter` opens one transaction per
            # claim, but that is a property of the caller, not of a buffered
            # batch adapter (review finding WR-07).
            P_SEQ: self._count(
                _FLUREE_ENTITY_CLAIM_COUNT, {**scope, "key": entity_uri}
            )
            + sum(
                1
                for buffered_claim in self._entity_claims
                if buffered_claim[P_ENTITY_URI] == entity_uri
            ),
            **_fluree_claim_projection(claim_json, kind=ENTITY_KIND),
        }
        # One object in two roles: the pending insert triple AND the buffer
        # `select_entity_chain` merges. They cannot drift because they are the
        # same dict.
        self._entity_claims.append(document)
        self._insert.append(document)
        return 1

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        scope = self._store.scope(tenant_id)
        rows: list[dict[str, Any]] = list(
            self._rows(_FLUREE_ENTITY_CHAIN, {**scope, "key": entity_uri})
        )
        rows += [
            {
                "claim_id": document[P_CLAIM_ID],
                "observed_at": document[P_OBSERVED_AT],
                "seq": document[P_SEQ],
            }
            for document in self._entity_claims
            if document[P_ENTITY_URI] == entity_uri
        ]
        # Stable sort on (observed_at, seq) — the graph rendering of
        # `ORDER BY observed_at, rowid`.
        rows.sort(key=lambda row: (row["observed_at"], row["seq"]))
        return rows

    def update_entity_supersession(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        matched = 0
        for document in self._entity_claims:
            if (
                document[P_CLAIM_ID] == claim_id
                and document[P_ENTITY_URI] == entity_uri
            ):
                self._apply_supersession(
                    document,
                    superseded_by=superseded_by,
                    superseded_at=superseded_at,
                )
                matched = 1
        if matched == 1:
            return matched
        held = self._rows(
            _FLUREE_ENTITY_CLAIM,
            {**scope, "key": entity_uri, "claim": claim_id},
        )
        if not held:
            return 0
        node_id = _mint_id(
            _FLUREE_ENTITY_CLAIM_KIND, partition, tenant_id, entity_uri, claim_id
        )
        self._replace(
            node_id, P_SUPERSEDED_BY, held[0]["superseded_by"], superseded_by
        )
        self._replace(
            node_id, P_SUPERSEDED_AT, held[0]["superseded_at"], superseded_at
        )
        return 1

    def upsert_relationship_node(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        relationship_type: str,
        subject_uri: str,
        object_uri: str,
        observed_at: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        node_id = _mint_id(
            _FLUREE_EDGE, partition, tenant_id, relationship_key
        )
        result = self._upsert_node(
            node_id=node_id,
            window_statement=_FLUREE_EDGE_WINDOW,
            window_params={**scope, "key": relationship_key},
            document={
                "@id": node_id,
                "@type": L_EDGE,
                P_PARTITION: partition,
                P_TENANT: tenant_id,
                P_RELATIONSHIP_KEY: relationship_key,
                P_RELATIONSHIP_TYPE: relationship_type,
                P_SUBJECT_URI: subject_uri,
                P_OBJECT_URI: object_uri,
                P_ADMIT_KEY: _RELATIONSHIP_ADMIT_PREFIX + relationship_key,
                P_FIRST_OBSERVED_AT: observed_at,
                P_LAST_OBSERVED_AT: observed_at,
            },
            observed_at=observed_at,
        )
        # The interposed-edge layout (15.3-RESEARCH.md §R5). A CCF relationship
        # is NOT a Cypher relationship here: on this engine a property-reading
        # relationship variable sees only reifier-bundled edges, so a hop
        # predicate stated on `r.prop` returns an empty reached set from a
        # query that answers 200 (Break 1); and the only bounded var-length
        # pattern admitted is a single fixed type, so the CCF type has nowhere
        # to live on the edge either (Break 2). Interposing a node moves both
        # onto node properties, where Cypher reads them reliably.
        #
        # Written ONCE, not doubled: Cypher's `-[:T]-` is first-class
        # undirected, so unlike `$graphLookup` (which follows
        # connectFromField -> connectToField in one direction and forced the
        # Mongo adapter to store every edge forward AND reverse) there is
        # nothing to compose around. Doubling would double the write cost for
        # nothing and create a second place for the layout to be wrong.
        #
        # The two links are maintained here, in the same buffered transaction
        # as the node they join — the layout cannot drift from the edge it
        # represents. Crossability is decided by the read path against the
        # surviving relationship claims, so this node carries identity and
        # endpoints only; it never carries admissibility.
        self._insert.append(
            {
                "@id": node_id,
                LINK_PREDICATE: [
                    {
                        "@id": _mint_id(
                            _FLUREE_ENTITY, partition, tenant_id, subject_uri
                        )
                    },
                    {
                        "@id": _mint_id(
                            _FLUREE_ENTITY, partition, tenant_id, object_uri
                        )
                    },
                ],
            }
        )
        return result

    def insert_relationship_claim(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        buffered = {row[P_CLAIM_ID] for row in self._relationship_claims}
        if claim_id in buffered:
            return 0
        identity: dict[str, object] = {
            **scope,
            "key": relationship_key,
            "claim": claim_id,
        }
        if self._rows(_FLUREE_RELATIONSHIP_CLAIM, identity):
            return 0
        node_id = _mint_id(
            _FLUREE_RELATIONSHIP_CLAIM_KIND,
            partition,
            tenant_id,
            relationship_key,
            claim_id,
        )
        document: dict[str, Any] = {
            "@id": node_id,
            "@type": L_RELATIONSHIP_CLAIM,
            P_PARTITION: partition,
            P_TENANT: tenant_id,
            P_RELATIONSHIP_KEY: relationship_key,
            P_CLAIM_ID: claim_id,
            P_CLAIM_JSON: claim_json,
            P_OBSERVED_AT: observed_at,
            P_POLICY_VERSION: policy_bundle_version,
            # Scoped to `relationship_key` on both terms, for the reason
            # `insert_entity_claim` states in full (review finding WR-07).
            P_SEQ: self._count(
                _FLUREE_RELATIONSHIP_CLAIM_COUNT,
                {**scope, "key": relationship_key},
            )
            + sum(
                1
                for buffered_claim in self._relationship_claims
                if buffered_claim[P_RELATIONSHIP_KEY] == relationship_key
            ),
            **_fluree_claim_projection(claim_json, kind=RELATIONSHIP_KIND),
        }
        self._relationship_claims.append(document)
        self._insert.append(document)
        return 1

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        scope = self._store.scope(tenant_id)
        rows: list[dict[str, Any]] = list(
            self._rows(
                _FLUREE_RELATIONSHIP_CHAIN, {**scope, "key": relationship_key}
            )
        )
        rows += [
            {
                "claim_id": document[P_CLAIM_ID],
                "observed_at": document[P_OBSERVED_AT],
                "seq": document[P_SEQ],
            }
            for document in self._relationship_claims
            if document[P_RELATIONSHIP_KEY] == relationship_key
        ]
        rows.sort(key=lambda row: (row["observed_at"], row["seq"]))
        return rows

    def update_relationship_supersession(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        matched = 0
        for document in self._relationship_claims:
            if (
                document[P_CLAIM_ID] == claim_id
                and document[P_RELATIONSHIP_KEY] == relationship_key
            ):
                self._apply_supersession(
                    document,
                    superseded_by=superseded_by,
                    superseded_at=superseded_at,
                )
                matched = 1
        if matched == 1:
            return matched
        held = self._rows(
            _FLUREE_RELATIONSHIP_CLAIM,
            {**scope, "key": relationship_key, "claim": claim_id},
        )
        if not held:
            return 0
        node_id = _mint_id(
            _FLUREE_RELATIONSHIP_CLAIM_KIND,
            partition,
            tenant_id,
            relationship_key,
            claim_id,
        )
        self._replace(
            node_id, P_SUPERSEDED_BY, held[0]["superseded_by"], superseded_by
        )
        self._replace(
            node_id, P_SUPERSEDED_AT, held[0]["superseded_at"], superseded_at
        )
        return 1

    def insert_lineage(
        self,
        *,
        tenant_id: str,
        claim_kind: str,
        node_key: str,
        claim_id: str,
        lineage_id: str,
        entry_json: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        fingerprint = (tenant_id, claim_kind, node_key, claim_id, lineage_id)
        if fingerprint in self._lineage:
            return 0
        held = self._count(
            _FLUREE_LINEAGE_COUNT,
            {
                **scope,
                "kind": claim_kind,
                "node": node_key,
                "claim": claim_id,
                "lineage": lineage_id,
            },
        )
        if held:
            return 0
        self._lineage.add(fingerprint)
        node_id = _mint_id(
            _FLUREE_LINEAGE,
            partition,
            tenant_id,
            claim_kind,
            node_key,
            claim_id,
            lineage_id,
        )
        self._insert.append(
            {
                "@id": node_id,
                "@type": L_LINEAGE,
                P_PARTITION: partition,
                P_TENANT: tenant_id,
                P_CLAIM_KIND: claim_kind,
                P_NODE_KEY: node_key,
                P_CLAIM_ID: claim_id,
                P_LINEAGE_ID: lineage_id,
                P_ENTRY_JSON: entry_json,
            }
        )
        # The returned integer carries the meaning, not the storage outcome:
        # ignore-on-conflict here IS the L-axis set-union (INV-CH7-17). RDF set
        # semantics would make the re-assertion a data no-op anyway, but the
        # contract needs the number resolved BEFORE commit, which is why the
        # read above is the authority rather than the substrate's behaviour.
        return 1


class FlureeGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one Fluree graph (plan 15.3-02).

    Same algorithm as every other writer, inherited rather than restated. What
    differs is the transaction: :class:`_FlureeTxn` implements the nine typed
    operations as one buffered JSON-LD batch — no SQL ``ClassVar`` statements
    are set here, exactly as the memory, Neo4j and Mongo backends.
    All-or-nothing on the failure path comes from the buffer: an exception
    drops it, and nothing was applied.

    Note what this docstring does **not** say, where its Mongo and Neo4j twins
    do: *extras-gated*. There is no extra. ``httpx`` is a core pin, so this
    writer needs no optional dependency, no lazy import and no mypy override —
    the SUBQ-14 evidence, visible as an absence.
    """

    def __init__(self, *, store: FlureeGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        txn = _FlureeTxn(store=self._store)
        try:
            yield txn
        except BaseException:
            txn.rollback()
            raise
        else:
            txn.commit()
