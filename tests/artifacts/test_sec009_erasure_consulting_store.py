"""SEC-009 step (2), in-process — the decorating store never serves erased bytes (`D-IMPL-374` (4)).

The hole as worded: an erased artifact is still served. Design ``D-IMPL-367``
§3: ONE consult behind the Protocol's reads, as a decorating store composed
around whatever store the deployment holds; an erased address raises
``ErasedContentRefused`` — never the bytes, and never ``ArtifactNotFound`` (the
silent-absence defect G5 forbids). ``exists`` does NOT consult (U8).

RED on a tree without the decorator: MISSING CONTRACT, reported in the body.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactNotFound, ArtifactStoreProtocol
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.composition import composition_register
from tests.erasure import harness as h

ERASED_AT = datetime(2026, 7, 30, tzinfo=UTC)
RECORD_ADDRESS = "f" * 64


def _erase(registry: ControlPlaneRegistry, address: str) -> None:
    h.erasure("append_to_erasure_index")(
        registry,
        composition_register(registry, h.erasure("erasure_index_key")(h.TENANT)),
        (
            h.erasure("ErasureIndexEntry")(
                content_address=address,
                erasure_record_address=RECORD_ADDRESS,
                reason="customer-request",
                erased_at=ERASED_AT,
            ),
        ),
    )


def _plane(tmp_path: Path) -> tuple[ControlPlaneRegistry, FileArtifactStore, Any, str, str]:
    registry = ControlPlaneRegistry()
    inner = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    erased = h.client_put(inner, name="erased", document={"customer": {"id": h.SUBJECT_ID}})
    kept = h.client_put(inner, name="kept", document={"customer": {"id": "someone-else"}})
    store = h.contract("ccf.erasure", "ErasureConsultingStore")(inner, index=h.erasure("ErasureIndex")(registry))
    _erase(registry, erased.content_address)
    return registry, inner, store, erased.uri, kept.content_address


def test_an_erased_artifact_is_never_served_in_process(tmp_path: Path) -> None:
    _registry, inner, store, erased_uri, _kept = _plane(tmp_path)
    address = inner.resolve_uri(uri=erased_uri)
    refused_type = h.contract("ccf.artifacts.protocol", "ErasedContentRefused")
    assert inner.get(content_address=address)  # the bytes are still on the substrate — no destruction is claimed
    with pytest.raises(refused_type) as refused:
        store.get(content_address=address)
    assert not isinstance(refused.value, ArtifactNotFound), "an erasure is not an absence (G5)"
    assert refused.value.erasure_record_address == RECORD_ADDRESS
    assert refused.value.reason == "customer-request"
    assert refused.value.erased_at == ERASED_AT
    assert h.SUBJECT_ID not in str(refused.value)


def test_resolving_the_name_of_an_erased_artifact_is_refused(tmp_path: Path) -> None:
    _registry, _inner, store, erased_uri, _kept = _plane(tmp_path)
    with pytest.raises(h.contract("ccf.artifacts.protocol", "ErasedContentRefused")):
        store.resolve_uri(uri=erased_uri)


def test_exists_answers_the_stores_truth_and_does_not_consult(tmp_path: Path) -> None:
    _registry, inner, store, erased_uri, _kept = _plane(tmp_path)
    assert store.exists(content_address=inner.resolve_uri(uri=erased_uri)) is True


def test_an_unerased_artifact_is_served_byte_identically_and_writes_pass_through(tmp_path: Path) -> None:
    _registry, inner, store, _erased_uri, kept = _plane(tmp_path)
    assert store.get(content_address=kept) == inner.get(content_address=kept)
    assert isinstance(store, ArtifactStoreProtocol)
    assert store.write_kinds is inner.write_kinds
    ref = h.client_put(store, name="later", document={"n": 1})
    assert inner.get(content_address=ref.content_address) == store.get(content_address=ref.content_address)
