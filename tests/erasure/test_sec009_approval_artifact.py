"""SEC-009 fix round 3 — the recorded approval is a durable artifact (`D-IMPL-374` (4), I3 part 2, option (a)).

At completion, BEFORE the index append, the door files the approval's record —
request, tenant, approver, verdict, instant, the gate and the state hash the
approver saw, the workflow definition's hash — as an immutable,
content-addressed ``ccf.erasure-approval``. ``approval_ref`` on the erasure
record and on the index entry IS that artifact's content address. The consult
``get``s it and requires it to name this request, this tenant and an approving
verdict; anything else is ``index-unsupported``. No plane beyond the
ArtifactStore is needed, so the check holds across a restart and a process.
The approval class is never erasable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.artifacts.protocol import DerivedWrite
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.principal import ApproverIdentity
from tests.erasure import composed
from tests.erasure import harness as h
from tests.erasure import signing
from tests.erasure.test_sec009_fix2 import _entry, _forged_record
from tests.composition import declared_erasure_trust


def _erased(plane: h.Plane) -> tuple[Any, Any]:
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    record = h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    assert isinstance(record, h.erasure("ErasureRecord")), record
    return request, record


def _fresh_consult(plane: h.Plane) -> tuple[Any, Any]:
    """A consult composed as a RESTARTED process composes it: a fresh registry's
    audit log, the index reopened from its file, nothing in memory — and the
    deployment's HITL policy, approval policy and erasure workflow re-registered
    at boot, as every boot registers what the deployment declares (fix round 4)."""
    booted = ControlPlaneRegistry()
    signing.register_signed_policy(booted, subject=h.APPROVER)
    composed.register_approval_policy(booted, tenant=h.TENANT)
    composed.register_erasure_workflow(booted, tenant=h.TENANT)
    audit = booted.audit_log
    consulted = h.erasure("compose_erasure_consult")(
        plane.store, index=h.index_of(plane), audit_log=audit, clock=h.fabric_clock, erasure_trust=declared_erasure_trust(), control_plane=booted, tenant_id=h.TENANT
    )
    return consulted, audit


def test_the_door_files_the_approval_the_record_names_it_and_it_survives_a_restart(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request, record = _erased(plane)
    approval = h.erasure("ErasureApproval").model_validate_json(plane.store.get(content_address=record.approval_ref))
    assert content_hash(approval) == record.approval_ref
    assert (approval.tenant_id, approval.request_id) == (h.TENANT, request.request_id)
    assert approval.verdict == "approve"
    assert approval.approver.subject_id == h.APPROVER
    assert approval.approver == record.actor
    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address)
    assert entry is not None and entry.approval_ref == record.approval_ref
    # And the check is durable: a RESTARTED consult (fresh audit log, index
    # reopened from its file) still supports the genuine erasure.
    consulted, audit = _fresh_consult(plane)
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=plane.document.content_address)
    assert refused.value.reason == record.reason
    assert refused.value.erasure_record_address == content_hash(record)
    assert not any(e.action == "erasure_index_unsupported" for e in audit.events())


@pytest.mark.parametrize("forgery", ["another-request", "another-tenant", "rejecting-verdict"])
def test_an_approval_that_does_not_approve_this_request_is_unsupported(tmp_path: Path, forgery: str) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = plane.document.content_address
    # Fix round 4: every forgery is SIGNED by the pinned key — a valid signature
    # over a claim set that does not approve THIS request — so what refuses it
    # is the claims check, not the signature check. Fix round 5: for the
    # DECLARED erasure workflow and its gate, and door-signed by the genuine
    # door key (the strongest forger), so neither R1 nor R2 refuses it first.
    tenant = "beta-bank" if forgery == "another-tenant" else h.TENANT
    request_id = "another-request" if forgery == "another-request" else request.request_id
    verdict = "reject" if forgery == "rejecting-verdict" else "approve"
    issued = h.fabric_clock()
    attestation = signing.sign(
        tenant=tenant, event_key=f"{tenant}/{request_id}/erasure-approval", product_content_hash="1" * 64,
        subject_id=h.APPROVER, issued_at=issued, action=verdict,
    )
    approver = ApproverIdentity(subject_id=h.APPROVER, identity_provider_ref="acme-bank/idp/okta")
    approval = h.erasure("ErasureApproval")(
        tenant_id=tenant,
        request_id=request_id,
        approver=approver,
        verdict=verdict,
        acted_at=issued,
        gate="erasure-approval",
        gate_state_hash="1" * 64,
        workflow_definition_hash=plane.definition_version,
        submission_hash="3" * 64,
        attestation=attestation,
        hitl_policy_ref=signing.policy_ref(plane.registry),
    )
    filed = plane.store.put(
        h.erase_cap(request),
        DerivedWrite(artifact_class=h.ERASURE_APPROVAL_CLASS, name=f"forged-{forgery}", artifact=approval),
    )
    record = _forged_record(request, address, approval_ref=filed.content_address, actor=approver)
    h.index_of(plane).append(h.erase_cap(request), _entry(request, address, content_hash(record), record=record, approval_ref=filed.content_address))
    plane.store.put(h.erase_cap(request), DerivedWrite(artifact_class=h.ERASURE_RECORD_CLASS, name="f" * 64, artifact=record))
    consulted, audit = _fresh_consult(plane)
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.get(content_address=address)
    assert refused.value.reason == "index-unsupported"
    assert any(e.action == "erasure_index_unsupported" for e in audit.events())


@pytest.mark.parametrize("mechanism_class", ["ccf.erasure-approval", "ccf.erasure-record"])
def test_the_approval_and_record_classes_are_never_declared_erasable(mechanism_class: str) -> None:
    with pytest.raises(ValidationError, match="never erasable"):
        h.erasure("ErasureSubjectClass")(
            class_id="customer",
            key_paths=("customer.id",),
            artifact_classes=(mechanism_class,),
            identifier_kind="opaque",
            subject_ref_salt="test-salt-not-a-secret",
        )
