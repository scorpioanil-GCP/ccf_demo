"""Replay resolves the EXACT store pin on a live ledger (24.5-L-02, criterion 6).

Whitepaper §7.10 (a decision reproduces against the exact fabric state at
decision time); CLAUDE.md §7.4 (replay resolves exact versions, never
"latest"); D-IMPL-240 (1); D-IMPL-88 (a transaction counter is not an as-of
instant). Built on plan 24.5-02's ``SnapshotPinnable`` Fluree reader.

The claim this module owes is the one the memory backend cannot make: a
product served at store pin ``N`` is **not reproducible from pin ``N+1``**,
and a ``SnapshotReader`` carrying the recorded pin re-renders the state at
``N`` byte-for-byte after the ledger has advanced — while the live reader,
unpinned, now answers something else. A fresh ledger is advanced *between*
the two reads so the difference is real rather than assumed.

Everything domain-shaped here is the conformance corpus's fixture vocabulary;
the reader under test knows none of it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.graph.backends.fluree import FLUREE_SUBSTRATE, FlureeGraphStore, FlureePinAhead
from ccf.graph.protocols import (
    NO_STORE_SNAPSHOT_PIN,
    GraphQuery,
    SnapshotPinnable,
    StoreSnapshotPin,
)
from ccf.replay.record import ContextFabricSnapshot
from ccf.replay.snapshots import SnapshotReader, SnapshotScopeViolation
from tests.conformance.query_corpus import chain_uris, entity_claim
from tests.conformance.test_substrate_properties import (
    PERMITTED_CLASSIFICATION,
    SEED_CLASS,
)
from tests.graph.test_fluree_backend import (
    TIMEOUT,
    _api_base,
    _claim_nodes,
    _fresh_ledger,
    _insert,
)

pytestmark = pytest.mark.fluree

PARTITION = "ccf"
OBSERVED = datetime(2026, 3, 1, tzinfo=UTC)
#: The as-of cut, after every claim's ``observed_at``: the pin — never the
#: as-of — is what distinguishes the reads below (D-IMPL-88).
BOUNDARY = datetime(2026, 4, 1, tzinfo=UTC)


def _snapshot_at(pin: StoreSnapshotPin, *, tenant: str, watermark: str) -> ContextFabricSnapshot:
    """A dimension-1 snapshot as ``build_replay_record`` would derive it, pinned at ``pin``."""
    return ContextFabricSnapshot.build(
        tenant_id=tenant,
        temporal_boundary=BOUNDARY,
        store_watermark=watermark,
        touched_entities=(),
        touched_relationships=(),
        store_snapshot_pin=pin,
    )


def test_a_product_served_at_pin_n_is_not_reproducible_from_pin_n_plus_1(
    fluree_url: str,
) -> None:
    """Criterion 6 on a live ledger, advanced between the reads.

    Two claims land the head at ``t=N`` (``N=2``); the reader's pin and the
    as-of view are taken. A third claim advances the head to ``N+1``. Then:

    (a) the live reader, unpinned, no longer answers the ``N`` view — the
        ledger really moved;
    (b) a ``SnapshotReader`` whose snapshot pins ``N`` answers ``as_of`` and
        the degenerate ``query`` byte-identical to the view taken at ``N``:
        the recorded pin is resolved exactly, however far the head went;
    (c) a ``SnapshotReader`` pinned at ``N+1`` answers a view that is NOT
        byte-identical to the ``N`` view — served at ``N`` is not
        reproducible from ``N+1``;
    (d) the pinned reader is itself ``SnapshotPinnable``, reports the
        recorded pin, admits only that pin on ``query_pinned``, and its
        execution-side pin equals the recorded one;
    (e) a snapshot pinned past the head is refused identifiably
        (``FlureePinAhead``) through the reader — never answered from the
        head.
    """
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    ledger = _fresh_ledger()
    first, second, third = (
        entity_claim(
            entity_uri=uri,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=OBSERVED,
            tenant_id=tenant,
        )
        for uri in (chain_uris(0)[0], chain_uris(1)[0], chain_uris(2)[0])
    )
    q = GraphQuery(tenant_id=tenant, as_of=BOUNDARY)

    with FlureeGraphStore(url=fluree_url, partition=PARTITION, ledger=ledger) as store:
        reader = store.reader
        assert isinstance(reader, SnapshotPinnable)
        with httpx.Client(timeout=TIMEOUT) as client:
            base, _ = _api_base(client, fluree_url)

            def advance(claim: object) -> int:
                receipt = _insert(
                    client,
                    base,
                    ledger,
                    _claim_nodes(claim, partition=PARTITION, policy_bundle_version="pb-1"),  # type: ignore[arg-type]
                )
                assert receipt.status_code == 200, receipt.text
                return int(receipt.json()["t"])

            assert advance(first) == 1
            n = advance(second)
            assert n == 2

            # The decision's read, at head N.
            pin_n = reader.snapshot_pin()
            assert pin_n == StoreSnapshotPin(substrate=FLUREE_SUBSTRATE, pin=str(n))
            view_n = reader.as_of(tenant_id=tenant, at=BOUNDARY)
            assert sorted(e.claim.entity_uri for e in view_n.entities) == sorted(
                (first.entity_uri, second.entity_uri)
            )
            watermark_n = content_hash(view_n)

            # The ledger moves on.
            assert advance(third) == n + 1

        # (a) the live head is no longer the N view.
        live = reader.as_of(tenant_id=tenant, at=BOUNDARY)
        assert len(live.entities) == 3
        assert canonical_bytes(live) != canonical_bytes(view_n)
        assert reader.snapshot_pin() == StoreSnapshotPin(
            substrate=FLUREE_SUBSTRATE, pin=str(n + 1)
        )

        # (b) the recorded pin re-renders N exactly, after the advance.
        at_n = SnapshotReader(
            reader=reader, snapshot=_snapshot_at(pin_n, tenant=tenant, watermark=watermark_n)
        )
        assert canonical_bytes(at_n.as_of(tenant_id=tenant, at=BOUNDARY)) == canonical_bytes(
            view_n
        )
        assert canonical_bytes(at_n.query(q)) == canonical_bytes(view_n)
        assert content_hash(at_n.as_of(tenant_id=tenant, at=BOUNDARY)) == watermark_n

        # (c) served at N is not reproducible from N+1.
        pin_n_plus_1 = StoreSnapshotPin(substrate=FLUREE_SUBSTRATE, pin=str(n + 1))
        at_n_plus_1 = SnapshotReader(
            reader=reader,
            snapshot=_snapshot_at(pin_n_plus_1, tenant=tenant, watermark=watermark_n),
        )
        later = at_n_plus_1.as_of(tenant_id=tenant, at=BOUNDARY)
        assert canonical_bytes(later) != canonical_bytes(view_n)
        assert canonical_bytes(later) == canonical_bytes(live)
        assert content_hash(later) != watermark_n

        # (d) the pinned reader is pinnable, reports the RECORDED pin, admits
        # only that pin — and both pins differ from the sentinel a SQL
        # deployment would record.
        assert isinstance(at_n, SnapshotPinnable)
        assert at_n.snapshot_pin() == pin_n != NO_STORE_SNAPSHOT_PIN
        assert canonical_bytes(at_n.query_pinned(q, pin=pin_n)) == canonical_bytes(view_n)
        with pytest.raises(SnapshotScopeViolation, match="different decision"):
            at_n.query_pinned(q, pin=pin_n_plus_1)

        # (e) past the head: refused through the reader, identifiably.
        ahead = SnapshotReader(
            reader=reader,
            snapshot=_snapshot_at(
                StoreSnapshotPin(substrate=FLUREE_SUBSTRATE, pin=str(n + 2)),
                tenant=tenant,
                watermark=watermark_n,
            ),
        )
        with pytest.raises(FlureePinAhead) as refused:
            ahead.as_of(tenant_id=tenant, at=BOUNDARY)
        assert f"t={n + 2}" in str(refused.value)
        assert fluree_url not in str(refused.value)
