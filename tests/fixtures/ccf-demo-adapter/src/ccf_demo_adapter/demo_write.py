"""The demo adapter's write path and the record the entry point names.

Plan 15.4-10, D-11. Four things live here: the connection contract, the nine
typed transaction operations over this adapter's dicts, the writer, and
``REGISTRATION``.

**Why the entry point names this module rather than the read module.** The
writer factory lives here. Pointing the declaration at
:mod:`ccf_demo_adapter.store` would put that factory on the import path of
everything that merely reads. So the direction is one-way and structural: this
module imports the read module freely, and the read module never imports this
one.

**This module imports the SDK's neutral write base, which is private by name
and restricted by a lint — and both halves of that are worth stating.**

The lint's tree scope is the SDK's own ``src`` and ``runtime``. It does not
reach a third-party adapter, and it was never meant to: it exists so that a
*core* module cannot reach for a write handle by accident, and a core module is
the only thing it can see.

The single-writer invariant does not depend on it reaching here. The mechanism
is the boot token: the SDK mints exactly one per graph identity and refuses a
second while the first is live, whoever asks and wherever they are installed.
That refusal is what a test asserts by booting twice on one ``graph_name``. The
lint is a layer above it, not the thing holding it up — which is why an adapter
outside the lint's reach is still inside the invariant.

The operations below are written against the write seam's own contract rather
than transcribed from an in-tree adapter. The conformance suite is the
specification; where a contract admits two readings, the test that asserts it
decides.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

from pydantic import SecretStr

from ccf.contracts.base import CCFContract
from ccf.graph._writer import BaseGraphWriter, BootToken, _GraphTxn
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, Row
from ccf.graph.registry import BackendRegistration, BackendStore

from ccf_demo_adapter.store import DemoGraphStore, _Claim, _GraphState, _Node

#: The name a manifest uses to select this adapter. It matches the registry's
#: required shape and is not one of the names the SDK's own adapter package
#: holds — a distribution claiming one of those is refused during discovery.
#: Deliberately outside ``__all__``: it is already answerable from
#: ``REGISTRATION.name``, and the registry refuses a record whose name disagrees
#: with the name it was resolved under, so the two cannot drift silently.
ADAPTER_NAME = "demo"

__all__ = ["REGISTRATION", "DemoConnection", "DemoGraphWriter"]


class DemoConnection(CCFContract):
    """The connection settings this adapter takes, and it takes no others.

    Deriving from :class:`~ccf.contracts.base.CCFContract` is load-bearing
    rather than stylistic: it supplies ``extra="forbid"`` and ``frozen=True``,
    and that inheritance *is* the refusal of a settings key this adapter does
    not declare. A model written against a plain open base would keep every
    valid manifest working and lose the refusal with nothing going red.

    ``secret_fields`` on the record below is empty, because there is nothing
    here to authenticate to.

    Attributes:
        graph_name: Which in-process graph this fabric opens. Required, and
            required for the same reason a file-backed adapter requires a path:
            it is what the graph identity is derived from, so the fabric must
            be told rather than left to invent one. Two fabrics given one name
            are two handles on one graph, and the second boot is refused while
            the first is live.
    """

    graph_name: str


class _DemoTxn:
    """The nine typed write operations, natively over this adapter's dicts.

    No SQL exists here and none is interpreted — each operation reads and
    writes the two dictionaries directly. Both of the seam's contract rules are
    honoured as the contract states them:

    * **Rowcounts resolve before commit.** The claim inserts return 0 for a
      re-arrival of a claim id already held, which is the writer's idempotency
      signal, and the lineage insert returns 0 on a collision against the full
      entry identity — which is what makes lineage accumulate by set union
      rather than by overwrite.
    * **Reads see this transaction's own operations.** Mutations land in the
      live dicts immediately, so a chain read includes claims appended earlier
      in the same transaction. Single-writer is what makes that safe: no other
      transaction's state exists to leak in.

    All-or-nothing comes from the owning writer. The graph's dicts are copied
    before this transaction first touches them, and :meth:`rollback` puts the
    copies back in place on the way out of a failure.
    """

    def __init__(self, *, state: _GraphState) -> None:
        self._state = state
        self._snapshot: tuple[
            dict[tuple[str, str, str], _Node],
            dict[tuple[str, str, str, str], _Claim],
        ] | None = None

    def _touch(self) -> _GraphState:
        """The graph's dicts, copied on first touch so a failure can undo."""
        if self._snapshot is None:
            self._snapshot = (
                copy.deepcopy(self._state.nodes),
                copy.deepcopy(self._state.claims),
            )
        return self._state

    def rollback(self) -> None:
        """Put the pre-transaction dicts back, in place.

        In place, deliberately: the store and its reader hold a reference to
        the same state object, so swapping the dicts out would leave them
        reading state this transaction was supposed to have undone.
        """
        if self._snapshot is None:
            return
        nodes, claims = self._snapshot
        self._state.nodes.clear()
        self._state.nodes.update(nodes)
        self._state.claims.clear()
        self._state.claims.update(claims)

    def _observe_node(
        self,
        *,
        tenant_id: str,
        kind: str,
        node_key: str,
        node_class: str,
        observed_at: str,
        subject_uri: str | None = None,
        object_uri: str | None = None,
    ) -> int:
        """Record one observation of a node, widening its observed window.

        One implementation for both axes, because the axis is already in the
        key. The window only ever widens — the earliest observation moves
        earlier and the latest moves later — and nothing is removed. Canonical
        text compares lexicographically as chronologically, so ``min`` and
        ``max`` are the whole of it.
        """
        state = self._touch()
        key = (tenant_id, kind, node_key)
        node = state.nodes.get(key)
        if node is None:
            state.nodes[key] = _Node(
                node_class=node_class,
                first_observed_at=observed_at,
                last_observed_at=observed_at,
                subject_uri=subject_uri,
                object_uri=object_uri,
            )
            return 1
        node.first_observed_at = min(node.first_observed_at, observed_at)
        node.last_observed_at = max(node.last_observed_at, observed_at)
        return 1

    def _append_claim(
        self,
        *,
        tenant_id: str,
        kind: str,
        node_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        """Append a claim, ignoring an exact re-arrival.

        Returns 1 for a claim this graph has not held before and 0 for one it
        already holds under the same identity. That number is the writer's
        whole idempotency signal, so returning 1 unconditionally would
        manufacture a supersession every time a source repeated itself.
        """
        state = self._touch()
        key = (tenant_id, kind, node_key, claim_id)
        if key in state.claims:
            return 0
        state.claims[key] = _Claim(
            node_key=node_key,
            claim_id=claim_id,
            claim_json=claim_json,
            observed_at=observed_at,
            policy_bundle_version=policy_bundle_version,
        )
        return 1

    def _chain(
        self, *, tenant_id: str, kind: str, node_key: str
    ) -> Sequence[Row]:
        """One node's whole claim chain, oldest first, ties by arrival.

        A stable sort over dict insertion order, which is this store's arrival
        order. Includes claims appended earlier in this same transaction,
        because the mutations above are already in the live dict.
        """
        state = self._touch()
        return tuple(
            sorted(
                (
                    claim
                    for (
                        claim_tenant,
                        claim_kind,
                        claim_node,
                        _id,
                    ), claim in state.claims.items()
                    if claim_tenant == tenant_id
                    and claim_kind == kind
                    and claim_node == node_key
                ),
                key=lambda claim: claim.observed_at,
            )
        )

    def _set_supersession(
        self,
        *,
        tenant_id: str,
        kind: str,
        node_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        """Set, or clear, one claim's supersession edge.

        The only mutation ever applied to a claim that already exists. Nothing
        else about a stored claim is ever reassigned and no claim is ever
        removed, which is what append-only-with-supersession means here.
        """
        state = self._touch()
        claim = state.claims.get((tenant_id, kind, node_key, claim_id))
        if claim is None:
            return 0
        claim.superseded_by = superseded_by
        claim.superseded_at = superseded_at
        return 1

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        return self._observe_node(
            tenant_id=tenant_id,
            kind=ENTITY_KIND,
            node_key=entity_uri,
            node_class=entity_class,
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
        return self._append_claim(
            tenant_id=tenant_id,
            kind=ENTITY_KIND,
            node_key=entity_uri,
            claim_id=claim_id,
            claim_json=claim_json,
            observed_at=observed_at,
            policy_bundle_version=policy_bundle_version,
        )

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        return self._chain(
            tenant_id=tenant_id, kind=ENTITY_KIND, node_key=entity_uri
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
        return self._set_supersession(
            tenant_id=tenant_id,
            kind=ENTITY_KIND,
            node_key=entity_uri,
            claim_id=claim_id,
            superseded_by=superseded_by,
            superseded_at=superseded_at,
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
        return self._observe_node(
            tenant_id=tenant_id,
            kind=RELATIONSHIP_KIND,
            node_key=relationship_key,
            node_class=relationship_type,
            observed_at=observed_at,
            subject_uri=subject_uri,
            object_uri=object_uri,
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
        return self._append_claim(
            tenant_id=tenant_id,
            kind=RELATIONSHIP_KIND,
            node_key=relationship_key,
            claim_id=claim_id,
            claim_json=claim_json,
            observed_at=observed_at,
            policy_bundle_version=policy_bundle_version,
        )

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        return self._chain(
            tenant_id=tenant_id,
            kind=RELATIONSHIP_KIND,
            node_key=relationship_key,
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
        return self._set_supersession(
            tenant_id=tenant_id,
            kind=RELATIONSHIP_KIND,
            node_key=relationship_key,
            claim_id=claim_id,
            superseded_by=superseded_by,
            superseded_at=superseded_at,
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
        """Append one lineage entry, ignoring one already recorded.

        Returns 1 for a genuinely new entry and 0 for a collision on the full
        entry identity. Ignore-on-collision here *is* the set union: a
        re-delivered envelope collides and is dropped, a second source
        corroborating the same claim does not.

        A missing claim is refused rather than absorbed. Every caller writes
        lineage against a claim it has just appended or just matched, so an
        absent one is a defect in the write path — and returning 0 would report
        it as a duplicate entry and lose the evidence silently.
        """
        state = self._touch()
        key = (tenant_id, claim_kind, node_key, claim_id)
        claim = state.claims.get(key)
        if claim is None:
            raise ValueError(
                f"adapter {ADAPTER_NAME!r}: lineage for a claim this graph does"
                f" not hold — kind {claim_kind!r}, claim {claim_id!r}"
            )
        if lineage_id in claim.lineage:
            return 0
        claim.lineage[lineage_id] = entry_json
        return 1


class DemoGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one demo graph.

    The write *semantic* is not restated here. Content identity, lineage set
    union, chain restitching and tenant-scope refusal all live once in the
    neutral base; this class contributes the transaction and nothing else. No
    SQL statements are set, and nothing in the base reads them for an adapter
    that answers the typed operations natively.
    """

    def __init__(self, *, store: DemoGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        txn = _DemoTxn(state=self._store.state)
        try:
            yield txn
        except BaseException:
            txn.rollback()
            raise


def _open_store(
    config: CCFContract, secrets: Mapping[str, SecretStr]
) -> BackendStore:
    """Construct this adapter's store from validated settings.

    The parameter is typed as the contract base so this function is assignable
    to the record's ``open_store`` field; the ``isinstance`` narrows it and says
    what arrived when it is not this adapter's model. ``secrets`` is unused:
    this adapter declares no credential, which is why its ``secret_fields`` is
    empty.
    """
    if not isinstance(config, DemoConnection):
        raise TypeError(
            f"adapter {ADAPTER_NAME!r} takes a {DemoConnection.__name__},"
            f" got a {type(config).__name__}"
        )
    return DemoGraphStore(graph_name=config.graph_name)


def _make_writer(store: BackendStore, token: BootToken) -> BaseGraphWriter:
    """Construct the write handle — called by the composition root alone."""
    if not isinstance(store, DemoGraphStore):
        raise TypeError(
            f"adapter {ADAPTER_NAME!r} writes through a"
            f" {DemoGraphStore.__name__}, got a {type(store).__name__}"
        )
    return DemoGraphWriter(store=store, token=token)


#: What this adapter declares about itself — the record the entry point names
#: and :func:`ccf.graph.registry.resolve` loads. Version and distribution are
#: deliberately absent: the registry derives both from this distribution's own
#: installed metadata, so the replay pin arrives for free and cannot be
#: misstated from here.
REGISTRATION = BackendRegistration(
    name=ADAPTER_NAME,
    config_model=DemoConnection,
    secret_fields=frozenset(),
    open_store=_open_store,
    make_writer=_make_writer,
)
