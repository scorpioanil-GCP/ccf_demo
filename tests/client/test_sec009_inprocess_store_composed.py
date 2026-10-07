"""SEC-009 ruling 2 — the in-process adapter's store is composed with the erasure consult (`D-IMPL-374` (4)).

RED today: ``ccf.client.adapters.inprocess._boot`` hands the resolver a raw
``FileArtifactStore`` that serves erased bytes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ccf.client.adapters.binding_document import load_binding_document
from ccf.client.adapters.inprocess import _boot
from tests.erasure import composed


def test_the_inprocess_adapters_store_composes_the_consult(seeded_root: Path) -> None:
    booted = _boot(load_binding_document(seeded_root), clock=lambda: datetime(2026, 7, 30, tzinfo=UTC))
    store = booted.resolver.artifact_store
    composed.assert_consults(store, store.index, control_plane=store.control_plane, tenant=store.tenant_id)
