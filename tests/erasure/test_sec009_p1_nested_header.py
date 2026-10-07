"""T4-P1 at the erasure consult: a nested JWS header in one index entry is that entry's problem only (SEC-009; `D-IMPL-374` (4), final fix wave FW-1).

The whole-branch review measured it: an index entry whose ``door_signature``
carries a deeply nested protected header made
``ccf.peering.identity.SignedContextProduct.declared_header`` raise an
uncaught ``RecursionError`` (its ``except`` covered only ``ValueError``), so
``compose_erasure_consult`` raised at EVERY store construction site — one
durable entry, filed by any holder of an erase capability for their own
request, took every store down. The ruled fix is in the shared parser: the
header becomes ``SignatureMalformed``, the consult reads the entry
``index-unsupported`` for its address, and nothing else changes.

The A2A admission and HITL attestation families of the same parser are held
by ``tests/peering/test_p1_nested_header_admission.py`` and
``tests/hitl/test_p1_nested_header_attestation.py``.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.composition import declared_erasure_authority
from tests.erasure import composed
from tests.erasure import harness as h
from tests.erasure import signing

#: Nested past any recursion limit the JSON decoder honors; measured, depth
#: 10 000 already raises on this interpreter. Test data, not a value the SDK reads.
DEPTH = 100_000


def _nested_header() -> str:
    """A base64url protected header that is a JSON array nested ``DEPTH`` deep."""
    text = "[" * DEPTH + "]" * DEPTH
    return base64.urlsafe_b64encode(text.encode("ascii")).rstrip(b"=").decode("ascii")


def test_p1_a_nested_header_entry_is_index_unsupported_for_its_address_only(tmp_path: Path) -> None:
    registry = ControlPlaneRegistry()
    raw = FileArtifactStore(root=tmp_path / "store", write_kinds=h.write_kinds())
    genuine = h.client_put(raw, name="genuine", document={"customer": {"id": "customer-1"}})
    victim = h.client_put(raw, name="victim", document={"customer": {"id": "customer-2"}})
    bystander = h.client_put(raw, name="bystander", document={"customer": {"id": "customer-3"}})
    # The bytes the forged entry names as its record: present, so the consult
    # reaches the door-signature check, and hashing to the address it is filed under.
    carrier = h.client_put(raw, name="carrier", document={"not": "an erasure record"})
    index = h.erasure("FileErasureIndex")(tmp_path / "idx" / ".erasure-index.jsonl")
    authority = declared_erasure_authority(h.TENANT)
    composed.erase(raw, index, genuine.content_address, control_plane=registry, authority=authority)
    composed.append_as(
        index,
        h.erasure("ErasureIndexEntry")(
            tenant_id=h.TENANT,
            content_address=victim.content_address,
            erasure_record_address=carrier.content_address,
            subject_class=h.SUBJECT_CLASS,
            request_id="p1-nested-header",
            subject_ref="ef" * 32,
            approval_ref="01" * 32,
            reason=composed.REASON,
            erased_at=datetime(2026, 7, 30, tzinfo=UTC),
            door_signature=f"{_nested_header()}..AAAA",
            door_key_id=signing.DOOR_KID,
        ),
    )

    # Composition survives the entry (before the fix: RecursionError here).
    store = h.erasure("compose_erasure_consult")(
        raw,
        index=index,
        audit_log=registry.audit_log,
        clock=h.fabric_clock,
        control_plane=registry,
        erasure_trust=h.erasure("ErasureTrust")(authorities={h.TENANT: authority}),
        tenant_id=h.TENANT,
    )

    refused = h.erasure("ErasedContentRefused")
    # The nested-header entry withholds its own address, as index-unsupported.
    with pytest.raises(refused) as unsupported:
        store.get(content_address=victim.content_address)
    assert unsupported.value.reason == h.erasure("INDEX_UNSUPPORTED")
    assert unsupported.value.erasure_record_address is None
    # The genuine erasure beside it is still judged supported, with its record's reason.
    with pytest.raises(refused) as supported:
        store.get(content_address=genuine.content_address)
    assert supported.value.reason == composed.REASON
    # An address no entry names is still served.
    assert store.get(content_address=bystander.content_address) == raw.get(
        content_address=bystander.content_address
    )
    # Audited once, for the nested-header entry's address and no other.
    unsupported_events = [
        event for event in registry.audit_log.events() if event.action == "erasure_index_unsupported"
    ]
    assert [event.key for event in unsupported_events] == [f"{h.TENANT}/{victim.content_address}"]
