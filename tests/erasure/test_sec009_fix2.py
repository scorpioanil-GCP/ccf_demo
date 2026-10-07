"""SEC-009 fix round 2 — the re-review's probes A, B and C inverted, plus I3, (a) and N3 (`D-IMPL-374` (4)).

* A (I3) — an erasure the requester files with its own erase capability and a
  FABRICATED approval reference is never SUPPORTED: with no recorded human
  approval on the audit plane, the entry is withheld as ``index-unsupported``.
* I3 — ``ErasureIndexProtocol.append`` requires the ``ArtifactErase`` capability
  bound to the entry's request; none, another request's, or a workflow's
  ``Resume`` is refused by name.
* B (I4) — a completion that dies at the index append is COMPLETED by a retry,
  never refused ``approval-not-recorded``, and the address ends withheld.
* C (N2) — the served ``reason`` and ``erased_at`` come from the RECORD; an
  entry that disagrees with its record is ``index-unsupported``.
* (a) — the index file is opened with ``O_NOFOLLOW``, owner = euid, mode 0600
  (parent 0700), refused by name otherwise; every line carries the hash of the
  previous one and a broken chain is refused.
* N3 — a corrupt index is a typed ``ErasureIndexCorrupt`` refusal that fails
  CLOSED: the store refuses every address under it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import DerivedWrite
from ccf.authz.capability import CapabilityBypassError
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.principal import ApproverIdentity
from tests.erasure import harness as h
from tests.erasure import signing

#: What an entry carries when the record it names does not exist: no record,
#: so nothing for a door to have signed (fix round 5) — the read fails first.
NO_RECORD_TO_SIGN = "no-record-to-sign"


def _entry(request: Any, address: str, record_address: str, *, record: Any = None, **overrides: Any) -> Any:
    """An index entry as a holder of ``ArtifactErase`` can append it.

    With ``record``, the entry carries the GENUINE door key's signature over it
    (fix round 5, R2) — the strongest forger, so whatever refuses the entry is a
    judgment AFTER the door signature, as each test intends.
    """
    values: dict[str, Any] = dict(
        tenant_id=h.TENANT, content_address=address, erasure_record_address=record_address,
        subject_class=request.subject_class, request_id=request.request_id,
        subject_ref=request.subject_ref, approval_ref="0" * 64, reason="customer-request",
        erased_at=h.fabric_clock(),
        door_signature=(
            NO_RECORD_TO_SIGN if record is None
            else h.erasure("sign_erasure_record")(record, signer=signing.door_provider(), key_id=signing.DOOR_KID)
        ),
        door_key_id=signing.DOOR_KID,
    )
    values.update(overrides)
    return h.erasure("ErasureIndexEntry")(**values)


def _forged_record(request: Any, address: str, **overrides: Any) -> Any:
    values: dict[str, Any] = dict(
        tenant_id=h.TENANT, record_id="f" * 64, request_id=request.request_id,
        subject_class=h.SUBJECT_CLASS, subject_ref=request.subject_ref,
        addresses=(h.erasure("ErasedAddress")(content_address=address, artifact_class=h.DOC_CLASS, key_paths=("customer.id",)),),
        erased_at=h.fabric_clock(),
        actor=ApproverIdentity(subject_id="nobody-approved", identity_provider_ref="x"),
        requested_by=h.REQUESTER, authorizing_decision_id="authz-decision-erase",
        approval_ref="0" * 64,
        retention_decision=h.erasure("RetentionDecision")(policy_ref=h.POLICY_URI, verdict="admit", reason_code="admitted"),
        reason="customer-request", legal_basis="forged",
    )
    values.update(overrides)
    return h.erasure("ErasureRecord")(**values)


def _consult(plane: h.Plane, audit: Any | None = None) -> Any:
    return h.erasure("compose_erasure_consult")(
        plane.store, index=h.index_of(plane), audit_log=audit or plane.registry.audit_log,
        clock=h.fabric_clock, erasure_trust=h.trust(plane), control_plane=plane.registry, tenant_id=h.TENANT,
    )


def test_a_a_requester_cannot_erase_without_a_recorded_approval(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = plane.document.content_address
    record = _forged_record(request, address)
    h.index_of(plane).append(h.erase_cap(request), _entry(request, address, content_hash(record), record=record))
    plane.store.put(h.erase_cap(request), DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name="f" * 64, artifact=record))
    audit = plane.registry.audit_log
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        _consult(plane, audit).get(content_address=address)
    assert not plane.transport.submissions(tenant=h.TENANT)  # no human ever approved
    assert refused.value.reason == "index-unsupported"
    assert any(e.action == "erasure_index_unsupported" for e in audit.events())


def test_append_requires_the_erase_capability_bound_to_the_request(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    entry = _entry(request, plane.document.content_address, "c" * 64)
    index = h.index_of(plane)
    with pytest.raises(TypeError):
        index.append(entry)  # no capability at all
    other = type(request).model_validate({**request.model_dump(), "legal_basis": "another request"})
    with pytest.raises(CapabilityBypassError):
        index.append(h.erase_cap(other), entry)
    with pytest.raises(CapabilityBypassError):
        index.append(h.resume_cap(), entry)
    assert index.lookup(tenant_id=h.TENANT, content_address=plane.document.content_address) is None
    index.append(h.erase_cap(request), entry)
    assert index.lookup(tenant_id=h.TENANT, content_address=plane.document.content_address) == entry


def test_b_a_completion_that_dies_at_the_append_is_completed_by_a_retry(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))

    def dying_append(*args: Any, **kwargs: Any) -> None:
        raise OSError("process killed at the index append")

    door._index.append = dying_append  # type: ignore[method-assign]
    with pytest.raises(OSError):
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    retry = h.door(plane)
    record = h.run(retry.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    assert isinstance(record, h.erasure("ErasureRecord")), record
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        _consult(plane).get(content_address=plane.document.content_address)
    assert refused.value.erasure_record_address == content_hash(record)


def test_c_the_served_facts_come_from_the_record_and_a_disagreeing_entry_is_unsupported(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    record = h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    with pytest.raises(h.erasure("ErasedContentRefused")) as genuine:
        _consult(plane).get(content_address=plane.document.content_address)
    assert (genuine.value.reason, genuine.value.erased_at) == (record.reason, record.erased_at)
    # A second document, whose entry claims a reason its record does not carry.
    other = h.client_put(plane.store, name="other", document={"customer": {"id": h.SUBJECT_ID}, "n": 2})
    forged = _forged_record(request, other.content_address, record_id="e" * 64)
    h.index_of(plane).append(h.erase_cap(request), _entry(request, other.content_address, content_hash(forged), record=forged, reason="court-order-7"))
    plane.store.put(h.erase_cap(request), DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name="e" * 64, artifact=forged))
    with pytest.raises(h.erasure("ErasedContentRefused")) as disagreeing:
        _consult(plane).get(content_address=other.content_address)
    assert disagreeing.value.reason == "index-unsupported"


def test_the_index_file_refuses_a_symlink_a_loose_mode_and_a_loose_parent(tmp_path: Path) -> None:
    index_type = h.erasure("FileErasureIndex")
    insecure = h.erasure("ErasureIndexInsecure")
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    real = private / "real.jsonl"
    real.write_bytes(b"")
    real.chmod(0o600)
    link = private / "link.jsonl"
    link.symlink_to(real)
    with pytest.raises(insecure):
        index_type(link)
    loose = private / "loose.jsonl"
    loose.write_bytes(b"")
    loose.chmod(0o644)
    with pytest.raises(insecure):
        index_type(loose)
    open_dir = tmp_path / "open"
    open_dir.mkdir(mode=0o755)
    open_dir.chmod(0o755)
    with pytest.raises(insecure):
        index_type(open_dir / "index.jsonl")
    index_type(private / "fresh.jsonl")  # the private, absent case opens


def test_a_broken_chain_and_a_corrupt_line_fail_closed_with_a_typed_refusal(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    index = h.index_of(plane)
    first = h.client_put(plane.store, name="one", document={"customer": {"id": h.SUBJECT_ID}, "n": 1})
    second = h.client_put(plane.store, name="two", document={"customer": {"id": h.SUBJECT_ID}, "n": 2})
    index.append(h.erase_cap(request), _entry(request, first.content_address, "c" * 64))
    index.append(h.erase_cap(request), _entry(request, second.content_address, "d" * 64))
    corrupt = h.erasure("ErasureIndexCorrupt")
    # Break the chain: drop the first line, so the second's predecessor is wrong.
    lines = plane.index_path.read_bytes().splitlines(keepends=True)
    plane.index_path.write_bytes(lines[1])
    os.chmod(plane.index_path, 0o600)
    with pytest.raises(corrupt):
        h.index_of(plane)
    # A garbage line: the store composes, then refuses EVERY address, typed.
    plane.index_path.write_bytes(b"".join(lines) + b"{not json}\n")
    os.chmod(plane.index_path, 0o600)
    audit = ControlPlaneRegistry().audit_log
    consulted = h.erasure("compose_erasure_consult")(
        plane.store, index=_LazyIndex(plane.index_path), audit_log=audit, clock=h.fabric_clock,
        erasure_trust=h.trust(plane), control_plane=plane.registry, tenant_id=h.TENANT,
    )
    untouched = plane.document.content_address
    with pytest.raises(corrupt) as refused:
        consulted.get(content_address=untouched)
    assert isinstance(refused.value, h.erasure("ErasedContentRefused"))
    assert refused.value.reason == "index-corrupt"


class _LazyIndex:
    """Opens the file index on first use, so a corrupt file reaches the READ path."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _open(self) -> Any:
        return h.erasure("FileErasureIndex")(self.path)

    def append(self, authorized: Any, entry: Any) -> None:
        self._open().append(authorized, entry)

    def lookup(self, *, tenant_id: str, content_address: str) -> Any:
        return self._open().lookup(tenant_id=tenant_id, content_address=content_address)

    def entries(self, *, tenant_id: str) -> Any:
        return self._open().entries(tenant_id=tenant_id)

    def tenants(self) -> Any:
        return self._open().tenants()


