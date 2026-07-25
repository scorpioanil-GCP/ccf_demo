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
does not add a writer module elsewhere.**

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

import json
import sqlite3

from ccf.contracts.canonical import canonical_timestamp, content_hash
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.backends.sqlite import (
    ENTITY_KIND,
    RELATIONSHIP_KIND,
    SqliteGraphStore,
)
from ccf.graph.protocols import UpsertResult

__ccf_mode__ = "algorithmic"

__all__ = [
    "BootToken",
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


_UPSERT_ENTITY_NODE = """
    INSERT INTO entities (
        tenant_id, entity_uri, entity_class, first_observed_at, last_observed_at
    ) VALUES (?, ?, ?, ?, ?)
    ON CONFLICT (tenant_id, entity_uri) DO UPDATE SET
        first_observed_at =
            MIN(entities.first_observed_at, excluded.first_observed_at),
        last_observed_at =
            MAX(entities.last_observed_at, excluded.last_observed_at)
"""

_INSERT_ENTITY_CLAIM = """
    INSERT OR IGNORE INTO entity_claims (
        tenant_id, entity_uri, claim_id, claim_json, observed_at,
        policy_bundle_version
    ) VALUES (?, ?, ?, ?, ?, ?)
"""

_SELECT_ENTITY_CHAIN = """
    SELECT claim_id, observed_at FROM entity_claims
    WHERE tenant_id = ? AND entity_uri = ?
    ORDER BY observed_at, rowid
"""

_UPDATE_ENTITY_SUPERSESSION = """
    UPDATE entity_claims SET superseded_by = ?, superseded_at = ?
    WHERE tenant_id = ? AND entity_uri = ? AND claim_id = ?
"""

_UPSERT_RELATIONSHIP_NODE = """
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

_INSERT_RELATIONSHIP_CLAIM = """
    INSERT OR IGNORE INTO relationship_claims (
        tenant_id, relationship_key, claim_id, claim_json, observed_at,
        policy_bundle_version
    ) VALUES (?, ?, ?, ?, ?, ?)
"""

_SELECT_RELATIONSHIP_CHAIN = """
    SELECT claim_id, observed_at FROM relationship_claims
    WHERE tenant_id = ? AND relationship_key = ?
    ORDER BY observed_at, rowid
"""

_UPDATE_RELATIONSHIP_SUPERSESSION = """
    UPDATE relationship_claims SET superseded_by = ?, superseded_at = ?
    WHERE tenant_id = ? AND relationship_key = ? AND claim_id = ?
"""

_INSERT_LINEAGE = """
    INSERT OR IGNORE INTO lineage (
        tenant_id, claim_kind, node_key, claim_id, lineage_id, entry_json
    ) VALUES (?, ?, ?, ?, ?, ?)
"""


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


class SqliteGraphWriter:
    """The single ``GraphWriter`` over one SQLite graph.

    Whitepaper §7.3; DESIGN.md §2A.5.3/§2A.5.4 step 4. Structurally conforms to
    :class:`ccf.graph.protocols.GraphWriter`.

    Args:
        store: The backend whose connection this writer mutates.
        token: The boot token authorizing this writer. Required, keyword-only,
            and single-use — omitting it is a ``TypeError`` and forging it is a
            :class:`SingleWriterViolation`.

    Raises:
        SingleWriterViolation: ``token`` is not a real token, was already
            spent, or authorizes a different graph than ``store``.
    """

    def __init__(self, *, store: SqliteGraphStore, token: BootToken) -> None:
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
        self._store = store
        self._closed = False

    def _connection(self) -> sqlite3.Connection:
        if self._closed:
            raise SingleWriterViolation(
                "this GraphWriter has been closed; obtain a new fabric through "
                "the composition root"
            )
        return self._store.connection

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
        connection: sqlite3.Connection,
        *,
        tenant_id: str,
        kind: str,
        node_key: str,
        claim_id: str,
        entries: frozenset[LineageEntry],
    ) -> int:
        """Accumulate lineage by set-union; return how many entries were new.

        ``INSERT OR IGNORE`` on the full entry identity *is* the set-union: a
        re-delivered envelope collides and is dropped, a second source does not
        (INV-CH7-17). Nothing here overwrites — an ``UPDATE`` of a lineage
        column would satisfy an idempotence test while destroying the
        multi-source evidence the L axis exists to hold.
        """
        before = connection.total_changes
        for entry in entries:
            connection.execute(
                _INSERT_LINEAGE,
                (
                    tenant_id,
                    kind,
                    node_key,
                    claim_id,
                    content_hash(entry),
                    json.dumps(entry.model_dump(mode="json"), sort_keys=True),
                ),
            )
        added = connection.total_changes - before
        return int(added)

    def _restitch_chain(
        self,
        connection: sqlite3.Connection,
        *,
        select_sql: str,
        update_sql: str,
        tenant_id: str,
        node_key: str,
        new_claim_id: str,
    ) -> str | None:
        """Recompute the supersession chain for one node by observed-time.

        Rewriting the whole chain rather than only linking the newest claim is
        what makes late-arriving observations behave: a claim observed *before*
        the current one slots into history already superseded, instead of
        wrongly displacing state the fabric learned later. The operation is
        idempotent, so a replayed write leaves the chain untouched.

        Returns the ``claim_id`` this write superseded, if any.
        """
        chain = connection.execute(select_sql, (tenant_id, node_key)).fetchall()
        superseded: str | None = None
        for position, row in enumerate(chain):
            is_last = position == len(chain) - 1
            successor = None if is_last else chain[position + 1]["claim_id"]
            successor_at = None if is_last else chain[position + 1]["observed_at"]
            connection.execute(
                update_sql,
                (successor, successor_at, tenant_id, node_key, row["claim_id"]),
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
        connection = self._connection()
        claim_id = content_hash(_entity_content_key(claim))
        observed_at = canonical_timestamp(claim.observed_at)
        payload = json.dumps(
            claim.model_dump(mode="json", exclude={"lineage"}), sort_keys=True
        )
        with connection:
            connection.execute(
                _UPSERT_ENTITY_NODE,
                (
                    tenant_id,
                    claim.entity_uri,
                    claim.entity_class,
                    observed_at,
                    observed_at,
                ),
            )
            cursor = connection.execute(
                _INSERT_ENTITY_CLAIM,
                (
                    tenant_id,
                    claim.entity_uri,
                    claim_id,
                    payload,
                    observed_at,
                    policy_bundle_version,
                ),
            )
            created = cursor.rowcount == 1
            lineage_added = self._write_lineage(
                connection,
                tenant_id=tenant_id,
                kind=ENTITY_KIND,
                node_key=claim.entity_uri,
                claim_id=claim_id,
                entries=claim.lineage,
            )
            superseded = (
                self._restitch_chain(
                    connection,
                    select_sql=_SELECT_ENTITY_CHAIN,
                    update_sql=_UPDATE_ENTITY_SUPERSESSION,
                    tenant_id=tenant_id,
                    node_key=claim.entity_uri,
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
        connection = self._connection()
        key = relationship_key(claim)
        claim_id = content_hash(_relationship_content_key(claim))
        observed_at = canonical_timestamp(claim.observed_at)
        payload = json.dumps(
            claim.model_dump(mode="json", exclude={"lineage"}), sort_keys=True
        )
        with connection:
            connection.execute(
                _UPSERT_RELATIONSHIP_NODE,
                (
                    tenant_id,
                    key,
                    claim.relationship_type,
                    claim.subject_uri,
                    claim.object_uri,
                    observed_at,
                    observed_at,
                ),
            )
            cursor = connection.execute(
                _INSERT_RELATIONSHIP_CLAIM,
                (
                    tenant_id,
                    key,
                    claim_id,
                    payload,
                    observed_at,
                    policy_bundle_version,
                ),
            )
            created = cursor.rowcount == 1
            lineage_added = self._write_lineage(
                connection,
                tenant_id=tenant_id,
                kind=RELATIONSHIP_KIND,
                node_key=key,
                claim_id=claim_id,
                entries=claim.lineage,
            )
            superseded = (
                self._restitch_chain(
                    connection,
                    select_sql=_SELECT_RELATIONSHIP_CHAIN,
                    update_sql=_UPDATE_RELATIONSHIP_SUPERSESSION,
                    tenant_id=tenant_id,
                    node_key=key,
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
