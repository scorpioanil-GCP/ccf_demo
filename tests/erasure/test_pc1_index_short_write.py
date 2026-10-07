"""PC1 (panel C1): a short write to the erasure index is never an append that "succeeded" (SEC-009; `D-IMPL-374`).

The cross-AI panel measured it (probes ``probe_b1_short_write{,_door}.py``):
``FileErasureIndex.append`` ignored ``os.write``'s count. A write that stops
short without raising — ENOSPC part-way, ``RLIMIT_FSIZE`` on the growing index,
some network filesystems — returned normally with a torn line; the reader skips
a line still being written, so ``lookup`` found nothing, the erasure door
resumed the workflow, filed the record and returned it, and the consulted store
kept SERVING the "erased" address. The next append merged into the torn line and
the index went corrupt (a total read outage under it).

Ruled: write until every byte is written; if that cannot complete, truncate the
file back to its pre-append length (no torn line), fsync, and raise
``ErasureIndexWriteFailed`` — which the door's completion propagates by name,
filing no record.

The failing write is modeled faithfully and offline: the index module's view of
``os`` is replaced so its FIRST ``write`` writes all but the last byte and
reports that count, and — for the case that cannot complete — every later write
fails with ``ENOSPC``, the disk-full sequence.
"""

from __future__ import annotations

import errno
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import ccf.erasure.index as index_module
from ccf.erasure.contracts import ErasureRecord
from tests.erasure import composed
from tests.erasure import harness as h


class _ShortThenFailing:
    """The index module's ``os``: one short write, then ``complete`` decides the rest."""

    def __init__(self, *, complete: bool) -> None:
        self._complete = complete
        self.writes = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(os, name)

    def write(self, descriptor: int, data: bytes) -> int:
        self.writes += 1
        if self.writes == 1:
            return os.write(descriptor, bytes(data[:-1]))
        if self._complete:
            return os.write(descriptor, data)
        raise OSError(errno.ENOSPC, "No space left on device")


def _entry(address: str, *, request_id: str = "pc1-request") -> Any:
    return h.erasure("ErasureIndexEntry")(
        tenant_id=h.TENANT,
        content_address=address,
        erasure_record_address="b" * 64,
        subject_class=h.SUBJECT_CLASS,
        request_id=request_id,
        subject_ref="d" * 64,
        approval_ref="e" * 64,
        reason=composed.REASON,
        erased_at=datetime(2026, 7, 30, tzinfo=UTC),
        door_signature="x..y",
        door_key_id="door-1",
    )


def _index(tmp_path: Path) -> Any:
    directory = tmp_path / "ix"
    return h.erasure("FileErasureIndex")(directory / ".erasure-index.jsonl")


def _raised(operation: Any) -> BaseException | None:
    try:
        operation()
    except Exception as raised:  # noqa: BLE001 - the outcome is the subject
        return raised
    return None


def test_pc1_a_write_that_cannot_complete_raises_by_name_and_leaves_no_torn_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = _index(tmp_path)
    composed.append_as(index, _entry("a" * 64, request_id="pc1-first"))
    before = index.path.read_bytes()

    proxy = _ShortThenFailing(complete=False)
    with monkeypatch.context() as patched:
        patched.setattr(index_module, "os", proxy)
        raised = _raised(lambda: composed.append_as(index, _entry("c" * 64)))
    assert raised is not None, "the append reported success over a write that could not complete"
    assert type(raised).__name__ == "ErasureIndexWriteFailed", repr(raised)
    assert isinstance(raised, h.erasure("ErasureIndexWriteFailed"))
    assert proxy.writes >= 2, "the append never tried to write the remainder"

    # No torn line: the file is exactly what it was before the failed append.
    assert index.path.read_bytes() == before
    assert index.lookup(tenant_id=h.TENANT, content_address="c" * 64) is None
    # The index is not corrupt: later appends and reads work, here and fresh.
    composed.append_as(index, _entry("c" * 64))
    assert index.lookup(tenant_id=h.TENANT, content_address="c" * 64) is not None
    fresh = h.erasure("FileErasureIndex")(index.path)
    assert fresh.lookup(tenant_id=h.TENANT, content_address="a" * 64) is not None
    assert fresh.lookup(tenant_id=h.TENANT, content_address="c" * 64) is not None


def test_pc1_a_short_write_that_can_complete_appends_the_whole_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = _index(tmp_path)
    proxy = _ShortThenFailing(complete=True)
    with monkeypatch.context() as patched:
        patched.setattr(index_module, "os", proxy)
        composed.append_as(index, _entry("c" * 64))
    assert proxy.writes >= 2
    assert index.path.read_bytes().endswith(b"\n")
    assert index.lookup(tenant_id=h.TENANT, content_address="c" * 64) is not None
    fresh = h.erasure("FileErasureIndex")(index.path)
    assert fresh.lookup(tenant_id=h.TENANT, content_address="c" * 64) is not None


def _stored_records(store: Any) -> list[str]:
    """Every stored artifact that parses as an erasure record."""
    found = []
    for path in Path(store.root).iterdir():
        if len(path.name) != 64:
            continue
        try:
            ErasureRecord.model_validate_json(path.read_bytes())
        except ValueError:
            continue
        found.append(path.name)
    return found


def test_pc1_the_door_does_not_complete_over_a_failed_append_and_its_retry_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(
        door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request))
    )
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))

    with monkeypatch.context() as patched:
        patched.setattr(index_module, "os", _ShortThenFailing(complete=False))
        raised = _raised(
            lambda: h.run(
                door.complete(
                    h.resume_cap(), definition_version=plane.definition_version, request=request,
                    resolution=resolution, erase=h.erase_cap(request),
                )
            )
        )
    assert raised is not None, "the door completed and returned a record over a write that could not complete"
    assert type(raised).__name__ == "ErasureIndexWriteFailed", repr(raised)
    assert _stored_records(plane.store) == [], "the door filed a record over a failed append"
    assert h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address) is None

    # The retry, on a working disk, completes the erasure: the record is
    # returned and the address is withheld with the record's own reason.
    record = h.run(
        door.complete(
            h.resume_cap(), definition_version=plane.definition_version, request=request,
            resolution=resolution, erase=h.erase_cap(request),
        )
    )
    assert isinstance(record, ErasureRecord)
    consulted = h.erasure("compose_erasure_consult")(
        plane.store, index=h.index_of(plane), audit_log=plane.registry.audit_log, clock=h.fabric_clock,
        erasure_trust=h.trust(plane), control_plane=plane.registry, tenant_id=h.TENANT,
    )
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=plane.document.content_address)
    assert refused.value.reason == request.reason
