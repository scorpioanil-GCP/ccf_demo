"""SEC-009 step (2), in-process — the decorating store never serves erased bytes (`D-IMPL-374` (4)).

The hole as worded: an erased artifact is still served. Design ``D-IMPL-367``
§3: ONE consult behind the Protocol's reads, as a decorating store composed
around whatever store the deployment holds; an erased address raises
``ErasedContentRefused`` — never the bytes, and never ``ArtifactNotFound`` (the
silent-absence defect G5 forbids). ``exists`` does NOT consult (U8).

RED on a tree without the decorator: MISSING CONTRACT, reported in the body.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactNotFound, ArtifactStoreProtocol
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.contracts.canonical import content_hash
from tests.erasure import composed
from tests.erasure import harness as h
from tests.composition import declared_hitl_policy_key

def _plane(tmp_path: Path) -> tuple[Any, FileArtifactStore, Any, str, str]:
    inner = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    erased = h.client_put(inner, name="erased", document={"customer": {"id": h.SUBJECT_ID}})
    kept = h.client_put(inner, name="kept", document={"customer": {"id": "someone-else"}})
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    registry = ControlPlaneRegistry()
    record = composed.erase(inner, index, erased.content_address, control_plane=registry)
    store = h.erasure("compose_erasure_consult")(
        inner, index=index, audit_log=registry.audit_log, clock=h.fabric_clock, hitl_policy_key=declared_hitl_policy_key(), control_plane=registry, tenant_id=h.TENANT
    )
    return record, inner, store, erased.uri, kept.content_address


def test_an_erased_artifact_is_never_served_in_process(tmp_path: Path) -> None:
    record, inner, store, erased_uri, _kept = _plane(tmp_path)
    address = inner.resolve_uri(uri=erased_uri)
    refused_type = h.erasure("ErasedContentRefused")
    assert inner.get(content_address=address)  # the bytes are still on the substrate — no destruction is claimed
    with pytest.raises(refused_type) as refused:
        store.get(content_address=address)
    assert not isinstance(refused.value, ArtifactNotFound), "an erasure is not an absence (G5)"
    assert refused.value.erasure_record_address == content_hash(record)
    assert refused.value.reason == composed.REASON
    assert refused.value.erased_at == composed.ERASED_AT
    assert h.SUBJECT_ID not in str(refused.value)


def test_resolving_the_name_of_an_erased_artifact_is_refused(tmp_path: Path) -> None:
    _record, _inner, store, erased_uri, _kept = _plane(tmp_path)
    with pytest.raises(h.erasure("ErasedContentRefused")):
        store.resolve_uri(uri=erased_uri)


def test_exists_answers_the_stores_truth_and_does_not_consult(tmp_path: Path) -> None:
    _record, inner, store, erased_uri, _kept = _plane(tmp_path)
    assert store.exists(content_address=inner.resolve_uri(uri=erased_uri)) is True


def test_an_unerased_artifact_is_served_byte_identically_and_writes_pass_through(tmp_path: Path) -> None:
    _record, inner, store, _erased_uri, kept = _plane(tmp_path)
    assert store.get(content_address=kept) == inner.get(content_address=kept)
    assert isinstance(store, ArtifactStoreProtocol)
    assert store.write_kinds is inner.write_kinds
    ref = h.client_put(store, name="later", document={"n": 1})
    assert inner.get(content_address=ref.content_address) == store.get(content_address=ref.content_address)
