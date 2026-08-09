"""The MongoDB graph write path — extras-gated (plan 15.2-13).

DESIGN.md §2A.5.3; whitepaper §7.3 (append-only-with-supersession graph state)
and INV-CH7-10 (only the Assembly worker holds a write handle). CCF SDK
extension surface: the module split itself is D-01 of Phase 15.4, not a
whitepaper commitment.

**This module is one of the modules CINV-02 guards.** The
``cinv02-graph-writer`` rule's guarded set is a *class* of modules — the
neutral base :mod:`ccf.graph._writer` plus every
``ccf.graph.backends.<name>_write`` — so this file joined the guard the moment
it existed, with no lint edit. Only ``ccf.assembly`` (L2) and ``ccf.boot`` (the
composition root) may import it. Threat T-15.2-06 is the reason the buffered
bulk operations below are here rather than beside the read pipeline.

**Import direction is one-way, and that is structural.** This module imports
its own reader module, :mod:`ccf.graph.backends.mongo`, freely — for the
collection names and the field-path helper. The reverse is forbidden: if the
reader imported the writer, every importer of the reader would transitively
reach write code and the CINV-02 rule would flag the reader itself. The write
module is therefore also where a ``REGISTRATION`` record belongs (plan
15.4-04).

The driver stays an optional extra. Importing this module imports the reader
module, which demands the driver at *store construction* rather than at import,
and :class:`_MongoTxn` defers its own driver import to construction for the
same reason — so a tree without the extra remains importable.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph._writer import BaseGraphWriter, BootToken, _GraphTxn
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
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, Row, parse_timestamp

__ccf_mode__ = "algorithmic"

__all__ = ["MongoGraphWriter"]


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
