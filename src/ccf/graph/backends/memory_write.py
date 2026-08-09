"""The in-memory graph write path — the Phase 15.2 D-06 KV floor.

DESIGN.md §2A.5.3; whitepaper §7.3 (append-only-with-supersession graph state)
and INV-CH7-10 (only the Assembly worker holds a write handle). CCF SDK
extension surface: the module split itself is D-01 of Phase 15.4, not a
whitepaper commitment.

**This module is one of the modules CINV-02 guards.** The
``cinv02-graph-writer`` rule's guarded set is a *class* of modules — the
neutral base :mod:`ccf.graph._writer` plus every
``ccf.graph.backends.<name>_write`` — so this file joined the guard the moment
it existed, with no lint edit. Only ``ccf.assembly`` (L2) and ``ccf.boot`` (the
composition root) may import it. That restriction is what keeps the reader
module's dicts read-only in practice as well as in principle: the row types
live there, every mutation of them lives here.

**Import direction is one-way, and that is structural.** This module imports
its own reader module, :mod:`ccf.graph.backends.memory`, freely. The reverse is
forbidden: if the reader imported the writer, every importer of the reader
would transitively reach write code and the CINV-02 rule would flag the reader
itself. The write module is therefore also where a ``REGISTRATION`` record
belongs (plan 15.4-04).

The first non-SQL proof of the typed write seam: :class:`_MemoryTxn` implements
the nine :class:`~ccf.graph._writer._GraphTxn` operations natively over the
store's per-tenant dicts, so no SQL text exists here and none is interpreted.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from ccf.graph._writer import BaseGraphWriter, BootToken, _GraphTxn
from ccf.graph.backends.memory import (
    EntityClaimRow,
    EntityNodeRow,
    LineageRow,
    MemoryGraphStore,
    RelationshipClaimRow,
    RelationshipNodeRow,
    TenantState,
)
from ccf.graph.reader import Row

__ccf_mode__ = "algorithmic"

__all__ = ["MemoryGraphWriter"]


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
