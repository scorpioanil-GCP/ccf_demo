"""SEC-009 fix round 4 — the erasure approval is bound to a SIGNED HITL attestation (`D-IMPL-374` (4); `D-IMPL-363`).

The re-review's probe D: a requester holding only ``ArtifactErase`` filed a
well-formed approving ``ccf.erasure-approval``, an entry and a record, with
zero HITL submissions, and the consult served the erasure as SUPPORTED. The
ruling binds the approval to the SEC-005 signed attestation:

1. the door refuses, by name, an approval that is unsigned or whose signature
   does not verify;
2. the approval artifact carries the signed claim set, the signature and the
   key id verbatim;
3. the consult verifies the signature against the key the pinned HITL policy
   declares for the approver, through its composed Control Plane, and requires
   the claims to name this request's gate, this tenant, the gate's state hash
   and an approving verdict — anything else is ``index-unsupported``, audited;
4. ``acted_at`` is the attestation's ``issued_at``, the human's own instant.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import DerivedWrite
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.principal import ApproverIdentity
from tests.erasure import harness as h
from tests.erasure import signing
from tests.erasure.test_sec009_fix2 import _entry, _forged_record


def _consult(plane: h.Plane) -> tuple[Any, Any]:
    """A consult composed as a restarted process composes it, over the plane's Control Plane."""
    audit = ControlPlaneRegistry().audit_log
    consulted = h.erasure("compose_erasure_consult")(
        plane.store, index=h.index_of(plane), audit_log=audit, clock=h.fabric_clock,
        control_plane=plane.registry, tenant_id=h.TENANT,
    )
    return consulted, audit


def _plant(plane: h.Plane, request: Any, approval: Any) -> str:
    """File ``approval``, an entry and a record naming it — only the requester's capability."""
    address = plane.document.content_address
    filed = plane.store.put(
        h.erase_cap(request), DerivedWrite(artifact_class=h.ERASURE_APPROVAL_CLASS, name="forged", artifact=approval)
    )
    record = _forged_record(request, address, approval_ref=filed.content_address)
    h.index_of(plane).append(h.erase_cap(request), _entry(request, address, content_hash(record), approval_ref=filed.content_address))
    plane.store.put(h.erase_cap(request), DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name="f" * 64, artifact=record))
    return address


def _assert_unsupported(plane: h.Plane, address: str) -> None:
    consulted, audit = _consult(plane)
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=address)
    assert not plane.transport.submissions(tenant=h.TENANT)  # no human ever acted
    assert refused.value.reason == "index-unsupported"
    assert any(e.action == "erasure_index_unsupported" for e in audit.events())


def _signed_forgery(plane: h.Plane, request: Any, *, directory: Path, event_key: str | None = None) -> Any:
    """A full-shape approval whose every claim is right for this request."""
    gate = "approval"
    issued = h.fabric_clock()
    attestation = signing.sign(
        tenant=h.TENANT,
        event_key=event_key or f"{h.TENANT}/{request.request_id}/{gate}",
        product_content_hash="1" * 64,
        subject_id="nobody-approved",
        issued_at=issued,
        directory=directory,
    )
    return h.erasure("ErasureApproval")(
        tenant_id=h.TENANT, request_id=request.request_id,
        approver=ApproverIdentity(subject_id="nobody-approved", identity_provider_ref="x"),
        verdict="approve", acted_at=issued, gate=gate, gate_state_hash="1" * 64,
        workflow_definition_hash="2" * 64, submission_hash="3" * 64,
        attestation=attestation, hitl_policy_ref=signing.policy_ref(plane.registry),
    )


def test_d_the_reviews_forgery_by_an_erase_capability_holder_is_unsupported(tmp_path: Path) -> None:
    """Probe D verbatim: the approval as the requester could file it before this round."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    forged = {
        "tenant_id": h.TENANT, "request_id": request.request_id,
        "approver": {"subject_id": "nobody-approved", "identity_provider_ref": "x"},
        "verdict": "approve", "acted_at": h.fabric_clock().isoformat(), "gate": "approval",
        "gate_state_hash": "1" * 64, "workflow_definition_hash": "2" * 64, "submission_hash": "3" * 64,
    }
    _assert_unsupported(plane, _plant(plane, request, forged))


def test_d_a_signature_by_a_key_the_policy_does_not_pin_is_unsupported(tmp_path: Path) -> None:
    """The strongest forger: every claim right, the pinned kid declared, other key material."""
    plane = h.compose(tmp_path)
    signing.register_signed_policy(plane.registry, subject="nobody-approved")
    request = h.request(plane)
    forged = _signed_forgery(plane, request, directory=signing.forger_key_dir())
    _assert_unsupported(plane, _plant(plane, request, forged))


def test_a_genuine_attestation_for_another_request_is_unsupported(tmp_path: Path) -> None:
    """A REAL signature by the pinned key, but naming another request's gate."""
    plane = h.compose(tmp_path)
    signing.register_signed_policy(plane.registry, subject="nobody-approved")
    request = h.request(plane)
    forged = _signed_forgery(
        plane, request, directory=signing.key_dir(), event_key=f"{h.TENANT}/another-request/approval"
    )
    _assert_unsupported(plane, _plant(plane, request, forged))


def test_the_door_refuses_an_unsigned_approval_by_name(tmp_path: Path) -> None:
    plane = h.compose(tmp_path, signed=False)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    assert refused.value.reason_code == "approval-unsigned"
    assert h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address) is None


class _TamperedTransport:
    """The plane's transport, answering ``submissions`` with a re-dated attestation."""

    def __init__(self, inner: Any, tamper: Any) -> None:
        self._inner = inner
        self._tamper = tamper

    def submissions(self, *, tenant: str) -> Any:
        return tuple(self._tamper(s) for s in self._inner.submissions(tenant=tenant))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_the_door_refuses_an_attestation_that_does_not_verify_by_name(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))

    def redate(submission: Any) -> Any:
        signed = submission.attestation
        claims = signed.claims.model_copy(update={"nonce": "substituted-after-signing"})
        return submission.model_copy(update={"attestation": signed.model_copy(update={"claims": claims})})

    tampered = resolution.model_copy(update={"record": resolution.record.model_copy(update={"submission": redate(resolution.record.submission)})})
    door._transport = _TamperedTransport(plane.transport, redate)
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=tampered, erase=h.erase_cap(request)))
    assert refused.value.reason_code == "approval-signature-invalid"


def test_the_approval_carries_the_attestation_and_acts_at_its_issued_at(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    record = h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    approval = h.erasure("ErasureApproval").model_validate_json(plane.store.get(content_address=record.approval_ref))
    assert approval.attestation == resolution.record.submission.attestation
    assert approval.attestation.key_id == signing.APPROVER_KID
    assert approval.acted_at == approval.attestation.claims.issued_at
    assert approval.hitl_policy_ref == signing.policy_ref(plane.registry)


def test_a_retry_after_dying_at_the_append_files_one_approval_not_two(tmp_path: Path) -> None:
    """Known behavior, asserted (re-review judgment 3): the approval is a function of
    the SIGNED attestation, so a retry re-files the SAME artifact — no orphan."""
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    filed: list[str] = []
    real_put = plane.store.put

    def recording_put(authorized: Any, artifact: Any) -> Any:
        ref = real_put(authorized, artifact)
        if isinstance(artifact, DerivedWrite) and artifact.artifact_class == h.ERASURE_APPROVAL_CLASS:
            filed.append(ref.content_address)
        return ref

    plane.store.put = recording_put  # type: ignore[method-assign]

    def dying_append(*args: Any, **kwargs: Any) -> None:
        raise OSError("process killed at the index append")

    real_append = door._index.append
    door._index.append = dying_append  # type: ignore[method-assign]
    with pytest.raises(OSError):
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    door._index.append = real_append  # type: ignore[method-assign]
    record = h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    assert len(filed) == 2 and len(set(filed)) == 1, filed
    assert record.approval_ref == filed[0]
