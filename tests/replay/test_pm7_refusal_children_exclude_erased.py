"""PM7 (panel C7): a refusal replay never claims to have verified an erased child (SEC-009; `D-IMPL-374`).

``RefusalReplayOutcome.child_contract_addresses`` is documented as *every
admitted child row's content address, each resolved from the store and
re-hashed to itself*. On the no-fabric-read path an erased admitted child is
SKIPPED — its bytes are never read, so nothing about it is re-hashed — and is
disclosed on ``erased_content``; but the address tuple was built from every
admitted row, so the evidence type's own field overstated what was verified.
After the repair an erased child's address is absent from the verified tuple
and present, positively, as an erased member.
"""

from __future__ import annotations

from typing import Any

from ccf.artifacts.file_store import FileArtifactStore
from ccf.erasure import FileErasureIndex, compose_erasure_consult
from ccf.replay.engine import RefusalReplayOutcome, replay_refusal
from ccf.replay.record import NO_FABRIC_READ
from tests.composition import declared_erasure_authority, declared_erasure_trust
from tests.erasure import composed
from tests.erasure import harness as h
from tests.products.composite_fixture import _Booted, _child_door, ask_composite
from tests.products.test_d_impl_339_child_contract_view import _ChildReadingFactory, _one_shot, _refused, _wired
from tests.products.test_d_impl_344_refusal_reconstruction import (  # noqa: F401 - the pytest fixture
    _NeverConsulted,
    _address_of,
    _admitted_addresses,
    booted_with_a_sibling,
)


def test_pm7_an_erased_child_is_disclosed_and_not_listed_as_verified(booted_with_a_sibling: _Booted) -> None:
    booted = booted_with_a_sibling
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    record = _refused(booted, outcome, "composite-child-refusal")
    (address,) = _admitted_addresses(record)
    assert record.content_generation_path.plan_id == NO_FABRIC_READ

    tenant = record.tenant_id
    index = FileErasureIndex(booted.store.root.parent / "pm7-index" / ".erasure-index.jsonl")
    composed.erase(
        booted.store, index, address, control_plane=booted.control_plane, tenant=tenant,
        authority=declared_erasure_authority(tenant),
    )
    fresh = FileArtifactStore(root=booted.store.root, write_kinds=booted.store.write_kinds)
    consulting = compose_erasure_consult(
        fresh, index=index, audit_log=booted.control_plane.audit_log, clock=h.fabric_clock,
        control_plane=booted.control_plane, erasure_trust=declared_erasure_trust(tenant), tenant_id=tenant,
    )

    reconstructed: Any = replay_refusal(
        record_address=_address_of(outcome, fresh),
        store=consulting,
        reader=booted.fabric.handle.reader,
        control_plane=booted.control_plane,
        environment=_NeverConsulted(),
    )
    assert isinstance(reconstructed, RefusalReplayOutcome), reconstructed
    # The erased child is disclosed, positively...
    assert any(
        member.content_address == address and member.site == "child-contract"
        for member in reconstructed.erased_content
    ), reconstructed.erased_content
    # ...and is NOT listed among the children resolved and re-hashed.
    assert address not in reconstructed.child_contract_addresses, (
        "the refusal replay lists an erased child as resolved and re-hashed"
    )
