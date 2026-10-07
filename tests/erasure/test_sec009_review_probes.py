"""SEC-009 fix round 1 — the review's probes P1–P5, inverted: each asserts the defect is ABSENT (`D-IMPL-374` (4)).

The reviewer's probes (`scratchpad/probe/test_probe_sec009.py`) each asserted a
defect was PRESENT and all five passed. Here each is committed red-first,
asserting the defect is gone:

* P1 (C2) — a requester's class label cannot bypass retention: the stored
  artifact's class decides, and a disagreeing label refuses by name.
* P2 (I1) — a raw identifier is refused as ``subject_ref``; a hold on the
  salted reference matches.
* P3 (I2) — ``requested_by`` is the RECORDED requester, never the presented one.
* P4 (C2) — an erasure record is never erasable.
* P5 (C1) — an erasure survives a restart: a reopened store over the same
  durable erasure index still refuses the erased address.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.authz.capability import ArtifactWrite, mint
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.erasure import harness as h
from tests.erasure import signing


def _full_erasure(plane: h.Plane, door: Any, request: Any) -> Any:
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    return h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.erase_cap(request)))


def _readdress(request: Any, address: str) -> Any:
    first = request.addresses[0].model_copy(update={"content_address": address})
    return type(request).model_validate({**request.model_dump(), "addresses": [first.model_dump()]})


def test_p1_a_mislabelled_class_cannot_bypass_retention(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    authorized = mint(
        ArtifactWrite,
        decision=h._allowed(action_id=ArtifactWrite.action_id, resource="severity-exempt-decision/d1"),
        principal="filer", decision_id="p1",
    )
    ref = plane.store.put(authorized, {"customer": {"id": h.SUBJECT_ID}, "decision": "significant"})
    request = _readdress(h.request(plane), ref.content_address)  # labelled kyc-note
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        _full_erasure(plane, h.door(plane), request)
    assert refused.value.reason_code == "class-label-mismatch"


def test_p2_a_raw_identifier_is_refused_and_a_hold_on_the_salted_ref_matches(tmp_path: Path) -> None:
    salted = h.erasure("subject_ref_for")(h.declaration(), h.SUBJECT_CLASS, h.SUBJECT_ID)
    plane = h.compose(tmp_path / "raw")
    with pytest.raises(ValidationError, match="subject_ref"):
        type(h.request(plane)).model_validate({**h.request(plane).model_dump(), "subject_ref": h.SUBJECT_ID})
    hold = h.erasure("LegalHold")(hold_id="H-1", subject_refs=(salted,), addresses=None, placed_at=h.NOW, placed_by="legal", basis="x")
    held = h.compose(tmp_path / "held", policy=h.retention(holds=(hold,)))
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        _full_erasure(held, h.door(held), h.request(held))
    assert refused.value.reason_code == "legal-hold" and refused.value.decision.hold_id == "H-1"


def test_p3_requested_by_is_the_recorded_requester_not_the_presented_one(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    forged_event = resolution.record.event.model_copy(update={"requested_by": "mallory"})
    forged = resolution.model_copy(update={"record": resolution.record.model_copy(update={"event": forged_event})})
    try:
        record = h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=forged, erase=h.erase_cap(request)))
    except h.door_module("ErasureRefused"):
        return  # refusing the forged presentation is also the defect absent
    assert record.requested_by == h.REQUESTER
    assert record.actor.subject_id == h.APPROVER


def test_p4_an_erasure_record_is_never_erasable(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    first = _full_erasure(plane, door, h.request(plane))
    record_address = content_hash(first)
    request = type(h.request(plane)).model_validate(
        {**_readdress(h.request(plane), record_address).model_dump(), "legal_basis": "second"}
    )
    with pytest.raises(h.door_module("ErasureRefused")):
        _full_erasure(plane, door, request)


def test_p5_an_erasure_survives_a_restart(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    record = _full_erasure(plane, h.door(plane), h.request(plane))
    address = plane.document.content_address
    # "Restart": the same artifact store on disk, the same durable erasure index
    # file, and a freshly booted Control Plane — as every SDK boot site builds.
    reopened = FileArtifactStore(root=tmp_path / "artifacts", write_kinds=h.write_kinds())
    assert reopened.exists(content_address=content_hash(record))
    index = h.erasure("FileErasureIndex")(h.index_path(plane))
    # The booted deployment re-registers its HITL policy (same content, same
    # pinned version) — the approval's signature verifies through it (fix round 4).
    booted = ControlPlaneRegistry()
    signing.register_signed_policy(booted, subject=h.APPROVER)
    consulted = h.erasure("compose_erasure_consult")(reopened, index=index, audit_log=booted.audit_log, clock=h.fabric_clock, control_plane=booted)
    with pytest.raises(h.erasure("ErasedContentRefused")):
        consulted.get(content_address=address)
    with pytest.raises(h.erasure("ErasedContentRefused")) as refused:
        consulted.scoped(h.TENANT).get(content_address=address)
    assert refused.value.reason == record.reason
