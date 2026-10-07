"""SEC-009 fix round 1 follow-up — the audit instant and memoized boot validation (`D-IMPL-374` (4)).

* Ruling 3 — the ``erasure_index_unsupported`` audit event is stamped with the
  fabric clock injected at composition, never with the disputed entry's own
  ``erased_at``.
* Ruling 4 — boot validation is memoized per index head (the index and its
  entry count), so two compositions over an unchanged index read each record
  once; a new append invalidates it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.erasure import composed
from tests.erasure import harness as h

FABRIC_NOW = datetime(2031, 1, 2, 3, 4, 5, tzinfo=UTC)


def _compose(store: Any, **kwargs: Any) -> Any:
    """Compose with the fabric clock; on a tree whose helper takes none, compose
    without it, so the control reports the BEHAVIOR (the audit instant, the
    record reads) rather than a signature error."""
    compose = h.erasure("compose_erasure_consult")
    try:
        return compose(store, clock=lambda: FABRIC_NOW, **kwargs)
    except TypeError as error:
        if "clock" not in str(error):
            raise
        return compose(store, **kwargs)


def test_the_index_unsupported_audit_is_stamped_with_the_injected_fabric_clock(tmp_path: Path) -> None:
    store = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    ref = h.client_put(store, name="n", document={"customer": {"id": h.SUBJECT_ID}})
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    entry = h.erasure("ErasureIndexEntry")(
        tenant_id=h.TENANT,
        content_address=ref.content_address,
        erasure_record_address="c" * 64,  # no such record: unsupported
        subject_class=h.SUBJECT_CLASS,
        request_id="req-audit-clock",
        subject_ref=composed.subject_ref(),
        approval_ref="a" * 64,
        reason="customer-request",
        erased_at=datetime(2026, 7, 30, tzinfo=UTC),
    )
    composed.append_as(index, entry)
    audit = ControlPlaneRegistry().audit_log
    _compose(store, index=index, audit_log=audit, tenant_id=h.TENANT)
    (event,) = [e for e in audit.events() if e.action == "erasure_index_unsupported"]
    assert event.occurred_at == FABRIC_NOW
    assert event.occurred_at != entry.erased_at


class _CountingStore:
    """The real file store, counting every byte read by address."""

    def __init__(self, inner: FileArtifactStore) -> None:
        self.inner = inner
        self.reads: list[str] = []

    def put(self, authorized: Any, artifact: Any) -> Any:
        return self.inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        self.reads.append(content_address)
        return self.inner.get(content_address=content_address)

    def exists(self, *, content_address: str) -> bool:
        return self.inner.exists(content_address=content_address)

    def resolve_uri(self, *, uri: str) -> str:
        return self.inner.resolve_uri(uri=uri)

    @property
    def root(self) -> Path:
        return self.inner.root


def test_two_compositions_over_an_unchanged_index_read_each_record_once(tmp_path: Path) -> None:
    raw = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    ref = h.client_put(raw, name="n", document={"customer": {"id": h.SUBJECT_ID}})
    index = h.erasure("FileErasureIndex")(tmp_path / "index.jsonl")
    record = composed.erase(raw, index, ref.content_address)
    from ccf.contracts.canonical import content_hash

    record_address = content_hash(record)
    counting = _CountingStore(raw)
    for _ in range(2):
        _compose(counting, index=index, audit_log=ControlPlaneRegistry().audit_log, tenant_id=h.TENANT)
    assert counting.reads.count(record_address) == 1, counting.reads
    # A new append invalidates the memo: the next composition validates again.
    other = h.client_put(raw, name="m", document={"customer": {"id": h.SUBJECT_ID}, "n": 2})
    second = composed.erase(raw, index, other.content_address)
    _compose(counting, index=index, audit_log=ControlPlaneRegistry().audit_log, tenant_id=h.TENANT)
    assert counting.reads.count(content_hash(second)) == 1
