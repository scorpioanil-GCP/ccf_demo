"""SEC-009 fix round 1 — the door VERIFIES every requester-named address (`D-IMPL-374` (4)).

Rulings (iii), (iv), C2, I6 and design §7:

* (iv) — every address must hold a value, at one of the subject's declared key
  paths, that hashes to the request's ``subject_ref``; else ``subject-not-found``.
* I6 — every address must be filed under the requesting tenant; else
  ``address-not-in-tenant``.
* C2 / (iii) — a store that answers no naming cannot have its stored class
  verified; the erasure is refused ``class-unverifiable``.
* §7, as ruled under ``D-IMPL-378`` (Dave, 2026-10-07 21:11 MST) — record
  retention (``replay-input``) applies only to a record the fabric's record
  writer filed; a principal's own client filing carrying the subject in a
  replay-input field is erased like any client artifact. The control (a record
  the writer filed still refuses ``replay-input``) and the stores that cannot
  attribute a filing are in ``tests/erasure/test_replay_input_retention_provenance.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.authz.capability import ArtifactWrite, mint
from ccf.authz.decision import AuthzDecision
from ccf.contracts.canonical import content_hash
from ccf.replay.provenance import filed_by_record_writer
from tests.erasure import harness as h


def _readdress(request: Any, address: str) -> Any:
    first = request.addresses[0].model_copy(update={"content_address": address})
    return type(request).model_validate({**request.model_dump(), "addresses": [first.model_dump()]})


def _request_refused(plane: h.Plane, request: Any, door: Any | None = None) -> Any:
    door = h.door(plane) if door is None else door
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    assert not plane.transport.pending(tenant=h.TENANT), "a refused request starts no approval"
    return refused.value


def test_an_address_whose_document_does_not_carry_the_subject_is_refused(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    other = h.client_put(plane.store, name="someone-else", document={"customer": {"id": "customer-99"}})
    refused = _request_refused(plane, _readdress(h.request(plane), other.content_address))
    assert refused.reason_code == "subject-not-found"


def test_an_address_filed_under_another_tenant_is_refused(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    foreign = "beta-bank"
    authorized = mint(
        ArtifactWrite,
        decision=AuthzDecision(
            allowed=True, matched_scope_pattern=foreign, matched_resource_pattern=f"{h.DOC_CLASS}/n",
            artifact_version="1.0.0", action_id=ArtifactWrite.action_id, tenant=foreign, resource=f"{h.DOC_CLASS}/n",
        ),
        principal="filer", decision_id="foreign",
    )
    ref = plane.store.put(authorized, {"customer": {"id": h.SUBJECT_ID}, "tenant": foreign})
    refused = _request_refused(plane, _readdress(h.request(plane), ref.content_address))
    assert refused.reason_code == "address-not-in-tenant"


class _NoNaming:
    """A store that answers the four Protocol verbs and no naming (an McpArtifactStore-shaped client)."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def put(self, authorized: Any, artifact: Any) -> Any:
        return self._inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        return bytes(self._inner.get(content_address=content_address))

    def exists(self, *, content_address: str) -> bool:
        return bool(self._inner.exists(content_address=content_address))

    def resolve_uri(self, *, uri: str) -> str:
        return str(self._inner.resolve_uri(uri=uri))


def test_a_store_that_answers_no_naming_cannot_verify_a_class_and_refuses(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane, store=_NoNaming(plane.store))
    refused = _request_refused(plane, h.request(plane), door=door)
    assert refused.reason_code == "class-unverifiable"


def test_a_client_filing_with_the_subject_in_a_replay_input_field_is_erased_like_any_client_artifact(
    tmp_path: Path,
) -> None:
    """Record retention is for records the fabric filed (``D-IMPL-378``; Dave, 2026-10-07 21:11 MST).

    **This test asserted the defect, and was renamed when it was changed.** It
    was ``test_a_subject_in_a_replay_input_field_refuses_replay_input``: it filed
    a principal's own client document carrying the subject at
    ``perspective_conditioning.principal_id`` and asserted that the door refused
    to erase it, ``replay-input``. Lane 378-provenance measured what that pinned:
    the door applied replay-input retention to ANY bytes with the subject in a
    replay-input field, so a tenant could make its own client file un-erasable by
    shaping it like a Decision Replay record. Dave's ruling (21:11 MST, "yes fix
    both now"): record-retention rules apply only to records the fabric's own
    record writer filed, decided by the one provenance check
    (``src/ccf/replay/provenance.py::filed_by_record_writer``).

    So the same document, filed the same way, is now erased like any client
    artifact: the request starts its approval, the recorded approval completes
    it, and the erasure record and the index entry name the address. Nothing else
    this test asserted is weakened: the subject is still in a replay-input field,
    and the filing is still the client lane's. The control — a record the
    fabric's record writer filed, with the subject in the same field, is still
    refused ``replay-input`` — is
    ``tests/erasure/test_replay_input_retention_provenance.py::test_a_record_the_fabrics_record_writer_filed_still_refuses_replay_input``.
    """
    plane = h.compose(tmp_path)
    ref = h.client_put(
        plane.store,
        name="pre-validator",
        document={"customer": {"id": h.SUBJECT_ID}, "perspective_conditioning": {"principal_id": h.SUBJECT_ID}},
    )
    request = _readdress(h.request(plane), ref.content_address)
    # The case is the one the old assertion rested on: the subject IS in a
    # replay-input field, and the store shows no filing by the record writer.
    assert "perspective_conditioning.principal_id" in h.erasure("REPLAY_INPUT_PATHS")
    assert filed_by_record_writer(plane.store, content_address=ref.content_address, tenant_id=h.TENANT) is False

    door = h.door(plane)
    suspended = h.run(
        door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request))
    )
    assert getattr(suspended, "event_key", None), suspended
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    record = h.run(
        door.complete(
            h.resume_cap(), definition_version=plane.definition_version, request=request,
            resolution=resolution, erase=h.erase_cap(request),
        )
    )
    assert isinstance(record, h.erasure("ErasureRecord")), record
    assert [a.content_address for a in record.addresses] == [ref.content_address]
    assert record.retention_decision.verdict == "admit"
    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=ref.content_address)
    assert entry is not None and entry.erasure_record_address == content_hash(record)
