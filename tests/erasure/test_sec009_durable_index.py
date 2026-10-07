"""SEC-009 fix round 1 — the durable erasure index and the record as the only authority (`D-IMPL-374` (4)).

Rulings C1 (with (i) and (ii)), I3, I4, I6, I7:

* C1 — ``ErasureIndexProtocol`` (``append``, ``lookup``, ``entries``,
  ``tenants``) with a file-backed reference implementation (append-only JSON
  lines, fsync on append, one file per deployment, keyed by tenant and
  address); REQUIRED at composition — no index, no composition, by name.
* §8 / I3 — the RECORD is the only authority: an entry whose record is absent
  or disagrees is withheld and audited ``erasure_index_unsupported``; erasure
  records are filed under the ``ArtifactErase`` kind, never a workflow's
  ``Resume``.
* I4 / (ii) — write-ahead: the door appends the entry BEFORE it files the
  record, so a record with no entry cannot exist.
* I6 / (i) — an erasure withholds within its tenant; a tenant-scoped view of
  another tenant serves the bytes; a tenantless read withholds with the reason
  and record address redacted.
* I7 — a read costs one ``lookup`` (O(1)), never a scan of ``entries``.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import DerivedWrite
from ccf.authz.capability import CapabilityBypassError
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.erasure import composed
from tests.erasure import harness as h

OTHER = "beta-bank"


def _entry(**overrides: Any) -> Any:
    values: dict[str, Any] = dict(
        tenant_id=h.TENANT,
        content_address="b" * 64,
        erasure_record_address="c" * 64,
        subject_ref=composed.subject_ref(),
        approval_ref="a" * 64,
        reason="customer-request",
        erased_at=datetime(2026, 7, 30, tzinfo=UTC),
    )
    values.update(overrides)
    return h.erasure("ErasureIndexEntry")(**values)


def _store(tmp_path: Path) -> FileArtifactStore:
    return FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())


def test_the_file_index_is_append_only_and_survives_a_reopen(tmp_path: Path) -> None:
    index_type = h.erasure("FileErasureIndex")
    path = tmp_path / "index.jsonl"
    index = index_type(path)
    entry = _entry()
    index.append(entry)
    index.append(entry)  # identical: idempotent
    with pytest.raises(h.erasure("ErasureIndexConflict")):
        index.append(_entry(erasure_record_address="d" * 64))  # never replaced
    reopened = index_type(path)
    assert reopened.lookup(tenant_id=h.TENANT, content_address=entry.content_address) == entry
    assert reopened.lookup(tenant_id=OTHER, content_address=entry.content_address) is None
    assert reopened.entries(tenant_id=h.TENANT) == (entry,)
    assert reopened.tenants() == frozenset({h.TENANT})
    assert isinstance(reopened, h.erasure("ErasureIndexProtocol"))
    # Another process's append is seen without reopening.
    index_type(path).append(_entry(tenant_id=OTHER))
    assert reopened.tenants() == frozenset({h.TENANT, OTHER})
    assert len(path.read_text().splitlines()) == 2


def test_composition_without_a_declared_index_refuses_by_name(tmp_path: Path) -> None:
    compose = h.erasure("compose_erasure_consult")
    parameters = inspect.signature(compose).parameters
    assert parameters["index"].default is inspect.Parameter.empty
    with pytest.raises(h.erasure("ErasureIndexUnavailable")):
        compose(_store(tmp_path), index=object(), audit_log=ControlPlaneRegistry().audit_log)


def test_an_entry_whose_record_is_missing_is_withheld_and_audited_index_unsupported(tmp_path: Path) -> None:
    store = _store(tmp_path)
    ref = h.client_put(store, name="n", document={"customer": {"id": h.SUBJECT_ID}})
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    index.append(_entry(content_address=ref.content_address))  # names a record nobody filed
    audit = ControlPlaneRegistry().audit_log
    consulted = h.erasure("compose_erasure_consult")(store, index=index, audit_log=audit, tenant_id=h.TENANT)
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=ref.content_address)
    assert refused.value.reason == "index-unsupported"
    assert refused.value.erasure_record_address is None
    assert any(event.action == "erasure_index_unsupported" for event in audit.events())


def test_a_genuine_record_validates_and_its_facts_are_served_to_its_own_tenant(tmp_path: Path) -> None:
    store = _store(tmp_path)
    ref = h.client_put(store, name="n", document={"customer": {"id": h.SUBJECT_ID}})
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    record = composed.erase(store, index, ref.content_address)
    audit = ControlPlaneRegistry().audit_log
    consulted = h.erasure("compose_erasure_consult")(store, index=index, audit_log=audit, tenant_id=h.TENANT)
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=ref.content_address)
    from ccf.contracts.canonical import content_hash

    assert refused.value.erasure_record_address == content_hash(record)
    assert refused.value.reason == "customer-request"
    assert not any(event.action == "erasure_index_unsupported" for event in audit.events())
    assert content_hash(record) not in str(refused.value)  # M8: the message carries no record address


def test_an_erasure_withholds_only_within_its_tenant(tmp_path: Path) -> None:
    store = _store(tmp_path)
    ref = h.client_put(store, name="shared", document={"customer": {"id": h.SUBJECT_ID}})
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    composed.erase(store, index, ref.content_address, tenant=h.TENANT)
    audit = ControlPlaneRegistry().audit_log
    root = h.erasure("compose_erasure_consult")(store, index=index, audit_log=audit)
    # Another tenant's view serves its own bytes and learns nothing.
    assert root.scoped(OTHER).get(content_address=ref.content_address)
    # The erasing tenant's view withholds, with the facts.
    with pytest.raises(h.erasure("ErasedContentRefused")) as own:
        root.scoped(h.TENANT).get(content_address=ref.content_address)
    assert own.value.reason == "customer-request"
    # A tenantless read withholds, redacted.
    with pytest.raises(h.erasure("ErasedContentRefused")) as tenantless:
        root.get(content_address=ref.content_address)
    assert tenantless.value.reason is None and tenantless.value.erasure_record_address is None


class _Counting:
    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls: dict[str, int] = {"append": 0, "lookup": 0, "entries": 0, "tenants": 0}

    def append(self, entry: Any) -> None:
        self.calls["append"] += 1
        self.inner.append(entry)

    def lookup(self, *, tenant_id: str, content_address: str) -> Any:
        self.calls["lookup"] += 1
        return self.inner.lookup(tenant_id=tenant_id, content_address=content_address)

    def entries(self, *, tenant_id: str) -> Any:
        self.calls["entries"] += 1
        return self.inner.entries(tenant_id=tenant_id)

    def tenants(self) -> Any:
        self.calls["tenants"] += 1
        return self.inner.tenants()


def test_a_scoped_read_costs_one_lookup_and_no_scan(tmp_path: Path) -> None:
    store = _store(tmp_path)
    inner = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    for n in range(50):
        inner.append(_entry(content_address=f"{n:064x}", erasure_record_address=f"{n + 1000:064x}"))
    counting = _Counting(inner)
    consulted = h.erasure("compose_erasure_consult")(
        store, index=counting, audit_log=ControlPlaneRegistry().audit_log, tenant_id=h.TENANT
    )
    ref = h.client_put(store, name="n", document={"k": 1})
    for key in counting.calls:
        counting.calls[key] = 0
    consulted.get(content_address=ref.content_address)
    assert counting.calls == {"append": 0, "lookup": 1, "entries": 0, "tenants": 0}


def test_an_erasure_record_cannot_be_filed_under_a_workflows_resume(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(CapabilityBypassError):
        store.put(h.resume_cap(), DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name="forged", artifact={"forged": True}))


def test_the_door_writes_the_index_entry_before_the_record(tmp_path: Path) -> None:
    """Write-ahead (I4, ruling (ii)): a completion that dies filing the record
    leaves the entry, so the approved erasure is ENFORCED (withheld, audited
    index-unsupported) — a record with no entry cannot exist."""
    plane = h.compose(tmp_path)
    real_put = plane.store.put

    def failing_put(authorized: Any, artifact: Any) -> Any:
        if isinstance(artifact, DerivedWrite) and artifact.artifact_class == h.ERASURE_RECORD_CLASS:
            raise OSError("disk full while filing the erasure record")
        return real_put(authorized, artifact)

    plane.store.put = failing_put  # type: ignore[method-assign]
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    with pytest.raises(OSError):
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address)
    assert entry is not None
    audit = ControlPlaneRegistry().audit_log
    consulted = h.erasure("compose_erasure_consult")(
        FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds()),
        index=h.index_of(plane), audit_log=audit, tenant_id=h.TENANT,
    )
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=plane.document.content_address)
    assert refused.value.reason == "index-unsupported"
