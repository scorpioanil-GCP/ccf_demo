"""SEC-009 step (1) — the erasure fact is written only through a governed door (`D-IMPL-374` (4)).

The hole as worded: *the fabric has no mechanism to erase a subject's content;
immutability has no counterpart for a right-to-erasure obligation* — and, for
this step, a write without an approval or under a legal hold has nothing to
refuse it. The ruled minimum (design `D-IMPL-367` §2.3, §4; U4, U9, U10):

* an ``ErasureRecord`` reaches the store only after a human approved the
  request through the ``ApprovalGate`` of a DEPLOYMENT-DECLARED workflow the
  door validates (U9) — the record names the approver and the requester;
* an approval the HITL authority path never recorded writes nothing;
* a legal hold refuses, by its hold id, at request and at completion;
* ``minimum_age`` is present on the contract with NO default (U10), and an
  artifact younger than it refuses;
* an absent class refuses (G7 default refuse);
* a replay-input path cannot be declared a subject key (U2), and a principal
  cannot be a subject this phase (U1).

RED on the base tree as MISSING CONTRACT (the door, the record and the policy do
not exist), reported inside each test body.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.hitl.approval_gate import GateResolution, HitlActionRecord
from ccf.skills.grants import ApprovalOutcome
from tests.erasure import harness as h


def _record_count(plane: h.Plane) -> int:
    """How many erasure records the store's naming index holds, for this tenant."""
    prefix = f"{h.TENANT}/{h.ERASURE_RECORD_CLASS}/"
    return sum(1 for key in plane.store._read_index() if key.startswith(prefix))


def _refusal_code(error: BaseException) -> str:
    return str(getattr(error, "reason_code", ""))


def test_an_erasure_record_is_written_only_after_a_human_approves_through_the_gate(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    # Requested, not erased: nothing is written and nothing is indexed until a human approves.
    assert getattr(suspended, "event_key", None), suspended
    assert _record_count(plane) == 0
    index = h.erasure("ErasureIndex")(plane.registry)
    assert index.lookup(plane.document.content_address) is None

    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    record = h.run(
        door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request))
    )
    assert isinstance(record, h.erasure("ErasureRecord")), record
    assert record.actor.subject_id == h.APPROVER
    assert record.requested_by == h.REQUESTER
    assert record.subject_ref == request.subject_ref and h.SUBJECT_ID not in record.subject_ref
    assert [a.content_address for a in record.addresses] == [plane.document.content_address]
    assert record.addresses[0].scope == "whole"
    assert record.retention_decision.verdict == "admit"
    # The record is filed through the store's one write verb, content-addressed.
    address = content_hash(record)
    assert plane.store.exists(content_address=address)
    assert _record_count(plane) == 1
    # And the registry mirror the consult reads names it.
    entry = index.lookup(plane.document.content_address)
    assert entry is not None and entry.erasure_record_address == address


def test_a_completion_presenting_an_approval_the_authority_path_never_recorded_writes_nothing(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    event = h.pending(plane, suspended.event_key)
    # A well-formed GateResolution for THIS suspension that the transport never
    # recorded: an eligible approver's verdict, fabricated rather than submitted.
    record = HitlActionRecord(
        event=event, submission=h.door_submission(event, subject_id=h.APPROVER), approved=True
    )
    forged = GateResolution(
        record=record,
        outcome=ApprovalOutcome(approved=True, approver_id=h.APPROVER),
        hitl_actions_block=canonical_bytes(record).decode("utf-8"),
    )
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=forged, erase=h.erase_cap(request)))
    assert _refusal_code(refused.value) == "approval-not-recorded"
    assert _record_count(plane) == 0
    assert h.erasure("ErasureIndex")(plane.registry).lookup(plane.document.content_address) is None


def test_a_workflow_with_no_approval_gate_is_refused_at_the_door(tmp_path: Path) -> None:
    plane = h.compose(tmp_path, gated=False)
    door = h.door(plane)
    with pytest.raises(h.door_module("ErasureWorkflowUngated")):
        h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=(r := h.request(plane)), erase=h.erase_cap(r)))
    assert not plane.transport.pending(tenant=h.TENANT)
    assert _record_count(plane) == 0


def test_a_legal_hold_refuses_the_request_and_names_its_hold(tmp_path: Path) -> None:
    probe = h.compose(tmp_path / "probe")
    subject_ref = h.request(probe).subject_ref
    hold = h.erasure("LegalHold")(
        hold_id="hold-7", subject_refs=(subject_ref,), addresses=None,
        placed_at=h.NOW, placed_by="counsel", basis="litigation",
    )
    plane = h.compose(tmp_path, policy=h.retention(holds=(hold,)))
    door = h.door(plane)
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=(r := h.request(plane)), erase=h.erase_cap(r)))
    decision = refused.value.decision
    assert decision.reason_code == "legal-hold" and decision.hold_id == "hold-7"
    assert decision.verdict == "refuse"
    assert not plane.transport.pending(tenant=h.TENANT)
    assert _record_count(plane) == 0


def test_a_legal_hold_placed_after_the_request_refuses_the_completion(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    hold = h.erasure("LegalHold")(
        hold_id="hold-late", subject_refs=None, addresses=(plane.document.content_address,),
        placed_at=h.NOW, placed_by="counsel", basis="regulator inquiry",
    )
    h.register_policy(plane.registry, h.retention(holds=(hold,), semver="1.1.0"))
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))
    assert refused.value.decision.reason_code == "legal-hold"
    assert refused.value.decision.hold_id == "hold-late"
    assert _record_count(plane) == 0
    assert h.erasure("ErasureIndex")(plane.registry).lookup(plane.document.content_address) is None


def test_minimum_age_is_present_on_the_contract_with_no_default() -> None:
    class_retention = h.erasure("ClassRetention")
    assert "minimum_age" in class_retention.model_fields
    assert class_retention.model_fields["minimum_age"].is_required()
    with pytest.raises(ValidationError):
        class_retention(erasable=True, reasons=("customer-request",))


def test_an_artifact_younger_than_the_minimum_age_is_refused(tmp_path: Path) -> None:
    plane = h.compose(tmp_path, policy=h.retention(minimum_age=timedelta(days=365 * 5)))
    door = h.door(plane)
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(
            door.request(
                h.execute_cap(), definition_version=plane.definition_version,
                request=(r := h.request(plane, retained_since=h.NOW - timedelta(days=30))), erase=h.erase_cap(r),
            )
        )
    assert refused.value.decision.reason_code == "under-minimum-age"
    assert _record_count(plane) == 0


def test_retention_defaults_to_refuse_for_an_undeclared_class(tmp_path: Path) -> None:
    empty = h.erasure("RetentionHoldPolicy")(semver="1.0.0", tenant_id=h.TENANT, classes={})
    plane = h.compose(tmp_path, policy=empty)
    door = h.door(plane)
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=(r := h.request(plane)), erase=h.erase_cap(r)))
    assert refused.value.decision.reason_code == "class-absent"
    # And a listed class is not erasable unless it says so.
    assert h.erasure("ClassRetention")(reasons=("x",), minimum_age=None).erasable is False


def test_a_replay_input_path_cannot_be_declared_a_subject_key_and_a_principal_cannot_be_a_subject() -> None:
    paths = h.erasure("REPLAY_INPUT_PATHS")
    assert "perspective_conditioning.principal_id" in paths
    with pytest.raises(ValidationError, match="replay input"):
        h.declaration(key_paths=("perspective_conditioning.principal_id",))
    with pytest.raises(ValidationError, match="replay input"):
        h.declaration(key_paths=("content_generation_path",))
    with pytest.raises(ValidationError, match="principal"):
        h.declaration(identifier_kind="principal")
