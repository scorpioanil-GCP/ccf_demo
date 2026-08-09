"""The neutral graph write base — layers 3 and 4 of the D-IMPL-41 stack.

DESIGN.md §2A.5.3; whitepaper §7.3 (append-only-with-supersession graph state)
and INV-CH7-10 (only the Assembly worker holds a write handle). The module
split this docstring describes is D-01 of Phase 15.4 — an SDK-defined
structural decision, not a whitepaper commitment.

**Why this module is private, and what it now holds.** The CINV-02 lint
restricts imports of ``ccf.graph._writer`` to ``ccf.assembly`` and ``ccf.boot``
— the L2 worker and the composition root — plus, since D-01, the backend
registry (which *types* the seam and never exercises it) and the guarded write
modules themselves. Every backend's writer class lives beside that backend's
reader, in ``ccf.graph.backends.<name>_write``; what remains here is the
substrate-neutral machinery those modules share.

**D-01 supersedes the old argument, and the rule did not have to be
redesigned.** This module used to argue that every backend's writer belonged
*here*, because a rule pinned to one file guards nothing once the write path
lives somewhere else. The premise was right and the conclusion was too narrow:
the fix is to guard a *class* of modules rather than one path. The
``cinv02-graph-writer`` rule's membership test is now the predicate
``is_write_module`` — this module, or any ``ccf.graph.backends.<name>_write`` —
so the same rule in its same shape covers seven files instead of one, and a
seventh adapter's write module joins the guarded set on arrival with no lint
edit. Nothing about *how* single-writer is enforced changed; only how many
modules the enforcement names.

**What stays here is not a matter of taste.** :data:`_LIVE_WRITERS` and
``_MINT_KEY`` are module-level mutable state, and they must live in **exactly
one module** or the invariant breaks: two copies of the live-writer table means
two graphs' worth of bookkeeping that never see each other, and "a writer
already exists for this graph" stops being answerable. Everything else here is
here because it is shared and substrate-neutral: the token, the content-key
helpers, the transaction Protocols, and the write semantic itself.

**One algorithm, many dialects.** :class:`BaseGraphWriter` holds the whole
write semantic — content identity, lineage set-union, chain restitching,
tenant-scope refusal — and a backend contributes only its transaction handling
and, for SQL backends, its statements. Two hand-written copies of the
supersession restitch would be two chances to get late-arriving observations
wrong, and the conformance suite could only tell us *that* they disagreed, not
which one was right. That is why the split moved the *dialects* out and left
the *semantic* in: a per-backend module that re-implemented supersession would
re-open exactly the drift this base closes.

**Why the write seam is typed operations, not SQL text (Phase 15.2).**
:class:`BaseGraphWriter` drives :class:`_GraphTxn` — nine typed graph-write
operations — rather than executing SQL statement constants directly. The
resolution is entailed, not discretionary: D-05/D-06 lock that every substrate
adapter runs under conformance suites whose writes go through booted L2
("nothing constructs a writer"), and neither a dict store, nor a graph engine,
nor a document store, nor an RDF ledger can execute SQL text. The alternative —
interpreting the nine SQL constants per backend — was considered and rejected:
one ad-hoc SQL interpreter per adapter would each be a private
re-implementation of this module's semantics, which is the exact drift the
shared base exists to prevent. SQL backends satisfy the seam through one shared
adapter (:class:`_SqlGraphTxn`) that drives the dialect ``ClassVar`` statements
unchanged; non-SQL backends implement the nine operations natively.

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
3. *Static gate* — the import restriction over this module **and every
   per-backend write module**, plus strict mypy, turn a write reference outside
   L2 into a CI failure.
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

import json
from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import ClassVar, Protocol

from ccf.contracts.canonical import (
    canonical_bytes,
    canonical_timestamp,
    content_hash,
)
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.protocols import UpsertResult
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, Row

__ccf_mode__ = "algorithmic"

__all__ = [
    "BaseGraphWriter",
    "BootToken",
    "SingleWriterViolation",
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
    Implementations live in this module or in a guarded per-backend write
    module — ``ccf.graph.backends.<name>_write``, never beside a reader
    (CINV-02, D-01; see the module docstring).

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

    **Why this one stayed central when the dialects left (D-01, D-03).** It is
    the only piece of write machinery that is *shared but not universal*, and
    that asymmetry is worth stating here rather than leaving a reviewer to
    discover it. Two of today's adapters drive it; a seventh SQL adapter would
    reuse it unchanged and contribute statements only; a seventh non-SQL
    adapter would never mention it. So it is neither per-backend (which would
    mean two copies of the same statement dispatcher, the drift
    :class:`BaseGraphWriter` exists to prevent) nor truly neutral (a non-SQL
    write module imports nothing from here but the base and the Protocol). It
    lives with the neutral base because the alternative — a home in one SQL
    adapter that the other imports — would make one backend's module a
    dependency of another's, which is the coupling D-IMPL-93 exists to remove.
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
