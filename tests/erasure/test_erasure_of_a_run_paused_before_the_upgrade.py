# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The erasure door refuses, before it writes anything, a run the engine will not resume (D-IMPL-391).

Design 1.4 binds an approval to the state store that paused the run: the engine
refuses a record another store wrote, and a run paused before the store identity
existed until ``WorkflowEngine.rebind_legacy_suspension`` re-pauses it for a fresh
approval (Dave's ruling 1(a) of 2026-10-17). The erasure door
(``runtime/ccf_runtime/erasure/door.py::ErasureDoor.complete``) judges the approval,
files it, and appends its write-ahead index entries BEFORE it asks the engine to
resume. Found by the independent review of the build: on a pre-upgrade run the
door appended entries naming the pre-upgrade approval, the engine then refused,
and every later completion — after the rebind and a fresh signed approval — was
refused ``approval-not-recorded``, because the entries named the old approval. The
address stayed withheld with no erasure record, for good.

The door now asks the engine's question first: a record whose identity is another
store's, or a suspended record with none, is refused ``workflow-refused`` before
anything is filed or appended, so the ruled path — rebind, fresh approval, complete
— finishes the erasure. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.state import state_key
from ccf.hitl.approval_gate import ApprovalGate, GateResolution
from ccf.hitl.transport import PendingHitlEvent
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.erasure import composed, signing
from tests.erasure import harness as h
from tests.hitl.capabilities import submit_capability
from tests.hitl.sec006_harness import door_submission

ANOTHER_STORE = "f" * 64


def _replant(plane: Any, request: Any, suspended: Any, *, identity: str | None) -> PendingHitlEvent:
    """Rewrite the persisted suspension as a pre-upgrade engine (``identity=None``)
    or another store wrote it, and re-file its request bound to that record."""
    key = state_key(tenant=h.TENANT, record_id=request.request_id)
    store = plane.registry.state_store
    record = store.get(WORKFLOW_STATE, key)
    fields = {n: getattr(record, n) for n in type(record).model_fields if n != "state_store_identity"}
    planted = WorkflowStateRecord(**fields, state_store_identity=identity)
    with store._write_lock:
        store._records[(WORKFLOW_STATE, key)] = planted
        store._versions[(WORKFLOW_STATE, key)] += 1
    filed = plane.transport.remove(tenant=h.TENANT, event_key=suspended.event_key)
    assert filed is not None
    plane.transport.enqueue(event=filed.model_copy(update={"product_content_hash": content_hash(planted)}))
    return h.pending(plane, suspended.event_key)


def _approve(plane: Any, event: PendingHitlEvent, *, nonce: str) -> GateResolution:
    """``harness.approve`` with its own nonce, so a second approval is not a replay."""
    gate = ApprovalGate(
        transport=plane.transport, audit=plane.registry.audit_log, clock=plane.clock,
        control_plane=plane.registry, hitl_policy_key=plane.hitl_policy_key,
        identity_provider=signing.provider(),
    )
    principal = door_submission(event, subject_id=h.APPROVER).principal
    attestation = signing.sign(
        tenant=h.TENANT, event_key=event.event_key, product_content_hash=event.product_content_hash,
        subject_id=h.APPROVER, issued_at=principal.action_time, nonce=nonce,
    )
    resolution = gate.resolve(
        submit_capability(tenant=h.TENANT, principal=h.APPROVER, event_key=event.event_key),
        event_key=event.event_key, action="approve", principal=principal, attestation=attestation,
    )
    assert isinstance(resolution, GateResolution), resolution
    return resolution


def _complete(plane: Any, request: Any, resolution: GateResolution) -> Any:
    return h.run(
        h.door(plane).complete(
            h.resume_cap(), definition_version=plane.definition_version,
            request=request, resolution=resolution, erase=h.erase_cap(request),
        )
    )


def _consult(plane: Any) -> str:
    consult = h.erasure("compose_erasure_consult")(
        plane.store, index=h.index_of(plane), audit_log=plane.registry.audit_log,
        clock=h.fabric_clock, erasure_trust=h.trust(plane), control_plane=plane.registry,
        tenant_id=h.TENANT,
    )
    try:
        consult.get(content_address=plane.document.content_address)
    except h.erasure("ErasedContentRefused") as refused:
        return "erased" if refused.reason == composed.REASON else f"withheld({refused.reason})"
    return "served"


def _start(tmp_path: Path) -> tuple[Any, Any, Any]:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    suspended = h.run(
        h.door(plane).request(
            h.execute_cap(), definition_version=plane.definition_version,
            request=request, erase=h.erase_cap(request),
        )
    )
    return plane, request, suspended


def test_a_run_paused_before_the_upgrade_is_refused_before_anything_is_written_and_then_completes(
    tmp_path: Path,
) -> None:
    plane, request, suspended = _start(tmp_path)
    legacy_request = _replant(plane, request, suspended, identity=None)
    pre_upgrade = _approve(plane, legacy_request, nonce="nonce-pre-upgrade")

    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        _complete(plane, request, pre_upgrade)

    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address)
    assert entry is None, "the door appended a write-ahead entry for a run the engine refuses"
    assert refused.value.reason_code == "workflow-refused", refused.value.reason_code
    assert "rebind_legacy_suspension" in str(refused.value)
    assert _consult(plane) == "served"

    workflow = h.door(plane)._factory.construct(h.resume_cap(), definition_version=plane.definition_version)
    rebound = plane.engine.rebind_legacy_suspension(
        h.resume_cap(), workflow, execution_id=request.request_id
    )
    fresh = _approve(plane, h.pending(plane, rebound.event_key), nonce="nonce-fresh")
    record = _complete(plane, request, fresh)

    assert type(record).__name__ == "ErasureRecord", record
    assert _consult(plane) == "erased"


def test_a_record_another_store_wrote_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    plane, request, suspended = _start(tmp_path)
    foreign_request = _replant(plane, request, suspended, identity=ANOTHER_STORE)
    approval = _approve(plane, foreign_request, nonce="nonce-foreign")

    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        _complete(plane, request, approval)

    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address)
    assert entry is None, "the door appended a write-ahead entry for a record another store wrote"
    assert refused.value.reason_code == "workflow-refused", refused.value.reason_code
    assert "other than this engine's" in str(refused.value)
    assert _consult(plane) == "served"
