# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-001's residual: an approval counts only in the state store that paused the run (D-IMPL-391).

Dave's ruling 1(a) of 2026-10-17 13:27 MST: *"Approval counts only in the store
that paused the run. Pre-upgrade paused runs are refused by name, re-paused with
an audit record, and need a fresh approval."* It carries decision 2 (b) of
2026-10-09 (*"Bind approval events and closures to the suspending state store's
stable identity ... One approval must authorize at most one passage."*) and the
10:54 MST ruling on design 1.4.

**The residual, as measured on ``3f914416``.** An approval was bound only to
``content_hash`` of the suspended
``runtime/ccf_runtime/workflow/state.py::WorkflowStateRecord``, which named no
store. Two independent stores that suspend the same execution at the same clock
readings write byte-identical suspensions, so one approval counted in both: two
passages on one approval, or a replacement store completing on another store's
verdict. Design 1.4 stamps every record with its store's identity
(``src/ccf/controlplane/state.py::ConditionalStateStore.identity``), so the
suspension hash every event, verdict, closure and passage name carries the
store, and the engine refuses by name a record another store wrote and a
suspension written before the change.

The stores here are the shared doubles of
``tests/workflow/test_engine_refuses_unsupported_seams.py`` (``SharedStore``,
``SharedTransport``): in-memory objects declaring ``scope = "shared"``, which is
how a deployment's own durable stores look to the engine. Every clock is the
suite's deterministic ticking clock, which is what makes two independent stores'
suspensions byte-identical before the change. New engine members are probed
with ``getattr``, so a red before the change fails on an assertion. Test
vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import InMemoryStateStore
from ccf.hitl.approval_gate import ApprovalGate
from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
from ccf.workflow.factory import Workflow
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowOutcome,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.hitl.capabilities import submit_capability
from tests.hitl.sec006_harness import execute_as_principal
from tests.workflow import test_engine as eh
from tests.workflow import test_sec006_engine_controls as s6
from tests.workflow.test_engine_refuses_unsupported_seams import SharedStore, SharedTransport
from tests.workflow.test_resume_single_flight import (
    APPROVER,
    DOWNSTREAM,
    EXECUTION,
    NEXT_GATE,
    STARTER,
    engine_over,
    plane,
    resume,
)

FIRST_GATE = "first-approval"
#: The engine's own refusal phrases (``WorkflowEngine._resume_claimed``).
NO_APPROVAL = "no approval for this suspension has returned through the HITL authority path"
FOREIGN = "written by a Control Plane state store other than this engine's"
LEGACY = "was suspended before the state store identity existed"
REBIND = "rebind_legacy_suspension"


class PlantableStore(InMemoryStateStore):
    """A process-scoped reference store whose persisted rows a test can set
    directly: what a durable store holds after an upgrade, or after a row was
    copied into it from another store."""

    def plant(self, key: str, record: object) -> None:
        with self._write_lock:
            self._records[(WORKFLOW_STATE, key)] = record
            self._versions[(WORKFLOW_STATE, key)] = (
                self._versions.get((WORKFLOW_STATE, key), 0) + 1
            )


class SharedPlantableStore(PlantableStore):
    scope = "shared"


class Deployment:
    """One process's engine over its own state store, beside a given transport."""

    def __init__(
        self,
        tmp_path: Path,
        *,
        store: InMemoryStateStore,
        transport: InMemoryHitlTransport,
        bindings: eh._Bindings,
    ) -> None:
        self.store = store
        self.transport = transport
        self.bindings = bindings
        self.registry: ControlPlaneRegistry = plane(store)
        self.workflow: Workflow = s6._two_gate(
            self.registry, eligible=frozenset({STARTER, APPROVER})
        )
        self.engine: WorkflowEngine = engine_over(self.registry, tmp_path, bindings, transport)
        self.tenant = self.workflow.definition.tenant
        self.key = f"{self.tenant}/{EXECUTION}"

    def start(self) -> WorkflowOutcome:
        starter = execute_as_principal(
            tenant=self.tenant, resource=self.workflow.definition_key, principal=STARTER
        )
        return asyncio.run(self.engine.execute(starter, self.workflow, execution_id=EXECUTION))

    def resume(self) -> WorkflowOutcome:
        return asyncio.run(resume(self.engine, self.workflow))

    def record(self) -> WorkflowStateRecord:
        held = self.store.get(WORKFLOW_STATE, self.key)
        assert isinstance(held, WorkflowStateRecord), held
        return held

    def approve(self, event_key: str) -> None:
        """One approval through the real ApprovalGate, on the oldest request under the key."""
        eh._resolve_gate(
            self.registry, self.transport, tenant=self.tenant,
            event_key=event_key, action="approve", subject_id=APPROVER,
        )


def passages(*deployments: Deployment) -> list[str | None]:
    """The attributed passages: ``workflow_resumed`` rows with ``resolved=True``."""
    return [
        event.actor
        for deployment in deployments
        for event in deployment.registry.audit_log.events()
        if event.action == "workflow_resumed" and event.resolved and event.key == deployment.key
    ]


def downstream_runs(bindings: eh._Bindings) -> int:
    return bindings.ran.count(f"skill:{DOWNSTREAM}")


def two_shared_stores(tmp_path: Path) -> tuple[Deployment, Deployment, InMemoryHitlTransport, eh._Bindings]:
    transport = SharedTransport()
    bindings = eh._Bindings()
    a = Deployment(tmp_path / "a", store=SharedStore(), transport=transport, bindings=bindings)
    b = Deployment(tmp_path / "b", store=SharedStore(), transport=transport, bindings=bindings)
    return a, b, transport, bindings


# --- B1: two independent stores behind one shared queue -----------------------------


def test_b1_one_approval_passes_only_in_the_store_that_paused_the_run(tmp_path: Path) -> None:
    """Two independent shared stores, one shared queue, the same execution id,
    one approval on A's request: A passes, B is refused for want of an approval,
    the step after the gate runs once, and the one passage and the one closure
    name A's suspension."""
    a, b, transport, bindings = two_shared_stores(tmp_path)
    started_a, started_b = a.start(), b.start()
    assert isinstance(started_a, WorkflowSuspended) and isinstance(started_b, WorkflowSuspended)
    suspension_a = content_hash(a.record())
    a.approve(started_a.event_key)

    passed = a.resume()
    refused = b.resume()

    assert isinstance(passed, WorkflowSuspended) and passed.gate == NEXT_GATE, passed
    assert isinstance(refused, WorkflowResumeRefused), (
        f"store B passed on store A's approval: {refused!r}"
    )
    assert NO_APPROVAL in refused.reason, refused.reason
    assert downstream_runs(bindings) == 1, (
        f"the step after the gate ran {downstream_runs(bindings)} times on one approval"
    )
    assert passages(a, b) == [APPROVER]
    assert [c.product_content_hash for c in transport.closures(tenant=a.tenant)] == [suspension_a]


# --- B2: a replacement store resumes on a verdict another store took ----------------


def test_b2_a_replacement_store_does_not_complete_on_another_stores_verdict(tmp_path: Path) -> None:
    """Store A is approved and never resumed; a replacement store B, beside the
    surviving shared queue, starts the same execution and resumes: refused."""
    transport = SharedTransport()
    bindings = eh._Bindings()
    a = Deployment(tmp_path / "a", store=SharedStore(), transport=transport, bindings=bindings)
    started_a = a.start()
    assert isinstance(started_a, WorkflowSuspended)
    a.approve(started_a.event_key)

    b = Deployment(tmp_path / "b", store=SharedStore(), transport=transport, bindings=bindings)
    assert isinstance(b.start(), WorkflowSuspended)
    outcome = b.resume()

    assert isinstance(outcome, WorkflowResumeRefused), (
        f"the replacement store passed on the verdict store A took: {outcome!r}"
    )
    assert NO_APPROVAL in outcome.reason, outcome.reason
    assert downstream_runs(bindings) == 0
    assert passages(a, b) == []


# --- B3: a store replaced after its run passed --------------------------------------


def test_b3_a_store_replaced_after_its_passage_gets_no_second_passage(tmp_path: Path) -> None:
    """Store A suspends, is approved and resumes; a replacement store B beside
    the surviving queue suspends the same execution and resumes: at most one
    passage on the one approval."""
    transport = SharedTransport()
    bindings = eh._Bindings()
    a = Deployment(tmp_path / "a", store=SharedStore(), transport=transport, bindings=bindings)
    started_a = a.start()
    assert isinstance(started_a, WorkflowSuspended)
    a.approve(started_a.event_key)
    assert isinstance(a.resume(), WorkflowSuspended)

    b = Deployment(tmp_path / "b", store=SharedStore(), transport=transport, bindings=bindings)
    assert isinstance(b.start(), WorkflowSuspended)
    outcome = b.resume()

    assert downstream_runs(bindings) == 1, (
        f"one approval released {downstream_runs(bindings)} passages"
    )
    assert len(passages(a, b)) == 1
    assert isinstance(outcome, WorkflowResumeRefused), outcome


# --- B5: a record another store wrote ------------------------------------------------


def test_b5_a_suspended_record_another_store_wrote_is_refused_by_name(tmp_path: Path) -> None:
    """A's suspended record, approved on A, copied into store B: B's engine
    refuses it by name and runs nothing."""
    transport = SharedTransport()
    bindings = eh._Bindings()
    a = Deployment(tmp_path / "a", store=SharedStore(), transport=transport, bindings=bindings)
    started_a = a.start()
    assert isinstance(started_a, WorkflowSuspended)
    a.approve(started_a.event_key)
    b = Deployment(
        tmp_path / "b", store=SharedPlantableStore(), transport=transport, bindings=bindings
    )
    assert isinstance(b.store, SharedPlantableStore)
    b.store.plant(b.key, a.record())

    outcome = b.resume()

    assert isinstance(outcome, WorkflowResumeRefused), (
        f"a record copied from store A passed in store B on A's approval: {outcome!r}"
    )
    assert FOREIGN in outcome.reason, outcome.reason
    assert downstream_runs(bindings) == 0
    refusals = [
        e for e in b.registry.audit_log.events()
        if e.action == "workflow_resumed" and not e.resolved and e.key == b.key
    ]
    assert len(refusals) == 1, "the refusal is audited resolved=False"


# --- B6, B7: a run paused before the upgrade -----------------------------------------


def legacy(record: WorkflowStateRecord) -> WorkflowStateRecord:
    """The same record as a pre-upgrade engine wrote it: no store identity."""
    fields = {
        name: getattr(record, name)
        for name in type(record).model_fields
        if name != "state_store_identity"
    }
    return WorkflowStateRecord(**fields)


def paused_before_the_upgrade(tmp_path: Path) -> tuple[Deployment, WorkflowStateRecord, PendingHitlEvent]:
    """A run suspended at its first gate whose persisted record and pending
    request are the pre-upgrade ones: the record carries no store identity, and
    the request is bound to that record's hash."""
    deployment = Deployment(
        tmp_path, store=PlantableStore(), transport=InMemoryHitlTransport(), bindings=eh._Bindings()
    )
    started = deployment.start()
    assert isinstance(started, WorkflowSuspended) and started.gate == FIRST_GATE
    old = legacy(deployment.record())
    store = deployment.store
    assert isinstance(store, PlantableStore)
    store.plant(deployment.key, old)
    filed = deployment.transport.remove(tenant=deployment.tenant, event_key=started.event_key)
    assert filed is not None
    request = filed.model_copy(update={"product_content_hash": content_hash(old)})
    deployment.transport.enqueue(event=request)
    assert [e.product_content_hash for e in deployment.transport.pending(tenant=deployment.tenant)] == [
        content_hash(old)
    ]
    return deployment, old, request


def rebind(deployment: Deployment) -> WorkflowOutcome:
    method = getattr(deployment.engine, REBIND, None)
    assert callable(method), f"WorkflowEngine offers no {REBIND}"
    outcome: WorkflowOutcome = method(
        eh.resume_as(deployment.workflow), deployment.workflow, execution_id=EXECUTION
    )
    return outcome


def test_b6_a_run_paused_before_the_upgrade_needs_a_fresh_approval(tmp_path: Path) -> None:
    """Approved before the upgrade: its resume is refused by name, naming the
    migration; the rebind re-pauses it under the same key with an audited
    ``workflow_suspended`` row; the old verdict authorizes nothing; one fresh
    approval releases exactly one passage."""
    deployment, old, request = paused_before_the_upgrade(tmp_path)
    deployment.approve(request.event_key)

    refused = deployment.resume()

    assert isinstance(refused, WorkflowResumeRefused), (
        f"a run paused before the upgrade passed on its pre-upgrade approval: {refused!r}"
    )
    assert LEGACY in refused.reason and REBIND in refused.reason, refused.reason
    assert downstream_runs(deployment.bindings) == 0

    suspended_rows = [
        e for e in deployment.registry.audit_log.events()
        if e.action == "workflow_suspended" and e.key == deployment.key
    ]
    rebound = rebind(deployment)
    assert isinstance(rebound, WorkflowSuspended), rebound
    assert rebound.gate == FIRST_GATE and rebound.event_key == request.event_key
    after = [
        e for e in deployment.registry.audit_log.events()
        if e.action == "workflow_suspended" and e.key == deployment.key
    ]
    assert len(after) == len(suspended_rows) + 1, "the re-pause is audited workflow_suspended"
    record = deployment.record()
    assert record.status == "suspended" and content_hash(record) != content_hash(old)

    stale = deployment.resume()
    assert isinstance(stale, WorkflowResumeRefused), (
        f"the pre-upgrade approval authorized the re-paused run: {stale!r}"
    )
    assert NO_APPROVAL in stale.reason, stale.reason

    deployment.approve(request.event_key)
    passed = deployment.resume()
    assert isinstance(passed, WorkflowSuspended) and passed.gate == NEXT_GATE, passed
    assert downstream_runs(deployment.bindings) == 1
    assert passages(deployment) == [APPROVER]


def test_b7_the_rebind_retires_the_pending_pre_upgrade_request(tmp_path: Path) -> None:
    """Paused before the upgrade with its request still pending and no approval:
    the rebind retires that request (audited) before it files the fresh one, so
    a fresh approval through the real ApprovalGate succeeds and passes once."""
    deployment, old, request = paused_before_the_upgrade(tmp_path)
    refused = deployment.resume()
    assert isinstance(refused, WorkflowResumeRefused), (
        f"a run paused before the upgrade was not refused: {refused!r}"
    )
    assert LEGACY in refused.reason, refused.reason

    rebound = rebind(deployment)
    assert isinstance(rebound, WorkflowSuspended), rebound
    fresh = content_hash(deployment.record())
    pending = deployment.transport.pending(tenant=deployment.tenant)
    assert [e.product_content_hash for e in pending] == [fresh], (
        "the pre-upgrade request is still pending beside the fresh one"
    )
    retired = [
        e for e in deployment.registry.audit_log.events()
        if e.action == "workflow_request_retired" and e.key == deployment.key
    ]
    assert len(retired) == 1 and retired[0].resolved, "the retirement is audited"

    gate = ApprovalGate(
        transport=deployment.transport, audit=deployment.registry.audit_log, clock=eh._ticking_clock()
    )
    resolution = gate.resolve(
        submit_capability(tenant=deployment.tenant, principal=APPROVER, event_key=request.event_key),
        event_key=request.event_key,
        action="approve",
        principal=eh._binding(fresh, subject_id=APPROVER, verdict="approve"),
    )
    assert resolution is not None
    passed = deployment.resume()
    assert isinstance(passed, WorkflowSuspended) and passed.gate == NEXT_GATE, passed
    assert downstream_runs(deployment.bindings) == 1


def test_b8_a_rebind_that_fails_before_its_fresh_request_lends_no_verdict_authority(
    tmp_path: Path,
) -> None:
    """Found by the independent review of the build. The rebind retired the
    pre-upgrade request through the transport's ``remove``, which records a
    claim on the key that only the fresh request's enqueue discards; when the
    re-pause stopped between the two (here, the artifact store failing at the
    trace write), the claim survived, and a verdict recorded afterwards with no
    request pending was stamped as a primitive's answer and carried the run past
    its gate — against ``D-IMPL-366`` H2. Now the trace and the state write come
    before the retirement, and the retirement sits next to the fresh enqueue:
    a failure at the trace write moves nothing, the stray verdict carries nothing
    past the gate, and the rebind presented again completes."""
    deployment, old, request = paused_before_the_upgrade(tmp_path)
    engine: Any = deployment.engine
    write_trace = engine._write_trace
    armed = {"fail": True}

    def fails_once(*args: Any, **kwargs: Any) -> Any:
        if armed["fail"]:
            armed["fail"] = False
            raise OSError("artifact store unavailable at the trace write")
        return write_trace(*args, **kwargs)

    engine._write_trace = fails_once
    with pytest.raises(OSError):
        rebind(deployment)

    current = content_hash(deployment.record())
    eh._submit_only(
        deployment.transport, tenant=deployment.tenant, event_key=request.event_key,
        product_content_hash=current, action="approve", subject_id=APPROVER,
    )
    outcome = deployment.resume()
    assert downstream_runs(deployment.bindings) == 0, (
        f"a verdict recorded with no request pending carried the run past its gate: {outcome!r}"
    )
    assert isinstance(outcome, WorkflowResumeRefused), outcome

    rebound = rebind(deployment)
    assert isinstance(rebound, WorkflowSuspended) and rebound.gate == FIRST_GATE, rebound


def test_residual_a_transport_failing_the_fresh_request_after_the_retirement_leaves_its_claim(
    tmp_path: Path,
) -> None:
    """RESIDUAL, disclosed on ``WorkflowEngine.rebind_legacy_suspension``. The
    retirement's ``remove`` records a claim on the key that only the fresh
    request's enqueue discards. Dave's answer of 2026-10-17 15:25 MST orders the
    retirement BEFORE the fresh request, so a transport that fails that one
    enqueue leaves the claim: a verdict recorded before the next resumption is
    stamped as a gate primitive's answer and carries the run past its gate. Without
    such a verdict, the next resumption restores the fresh request, which discards
    the claim, and nothing passes. Goes red if the window is closed (for example by
    filing the fresh request before the retirement), and must then be rewritten to
    assert the closing mechanism."""
    deployment, old, request = paused_before_the_upgrade(tmp_path)
    transport: Any = deployment.transport
    enqueue = transport.enqueue
    armed = {"fail": True}

    def fails_once(*, event: PendingHitlEvent) -> None:
        if armed["fail"]:
            armed["fail"] = False
            raise OSError("transport unavailable at the fresh request")
        enqueue(event=event)

    transport.enqueue = fails_once
    with pytest.raises(OSError):
        rebind(deployment)
    retired = [
        e for e in deployment.registry.audit_log.events()
        if e.action == "workflow_request_retired" and e.key == deployment.key
    ]
    assert len(retired) == 1, "the retirement is audited even though the fresh request failed"

    stray = eh._submit_only(
        deployment.transport, tenant=deployment.tenant, event_key=request.event_key,
        product_content_hash=content_hash(deployment.record()), action="approve", subject_id=APPROVER,
    )
    assert stray.event_state_at_submit == "claimed", "the residual: the claim stamps the stray verdict"
    outcome = deployment.resume()
    assert isinstance(outcome, WorkflowSuspended) and outcome.gate == NEXT_GATE, outcome
    assert downstream_runs(deployment.bindings) == 1


def test_a_retried_start_never_restores_a_request_for_a_run_paused_before_the_upgrade(
    tmp_path: Path,
) -> None:
    """``WorkflowEngine._finish_start``: a pre-upgrade pause whose request is
    gone is refused as a second start, never restored under its legacy hash (the
    rebind re-pauses it)."""
    deployment, old, request = paused_before_the_upgrade(tmp_path)
    assert deployment.transport.dequeue(tenant=deployment.tenant) == request

    again = deployment.start()

    assert isinstance(again, WorkflowResumeRefused), (
        f"a retried start restored a request bound to the pre-upgrade suspension: {again!r}"
    )
    assert "already exists" in again.reason, again.reason
    assert deployment.transport.pending(tenant=deployment.tenant) == ()


def test_a_retried_start_never_finishes_a_record_another_store_wrote(tmp_path: Path) -> None:
    """``WorkflowEngine._finish_start``: a suspension copied in from another store,
    its request gone, is refused as a second start; nothing is filed."""
    deployment = Deployment(
        tmp_path, store=PlantableStore(), transport=InMemoryHitlTransport(), bindings=eh._Bindings()
    )
    started = deployment.start()
    assert isinstance(started, WorkflowSuspended)
    copied = legacy(deployment.record()).model_copy(update={"state_store_identity": "f" * 64})
    store = deployment.store
    assert isinstance(store, PlantableStore)
    store.plant(deployment.key, copied)
    assert deployment.transport.dequeue(tenant=deployment.tenant) is not None

    again = deployment.start()

    assert isinstance(again, WorkflowResumeRefused), (
        f"a retried start acted on a record another store wrote: {again!r}"
    )
    assert deployment.transport.pending(tenant=deployment.tenant) == ()


def test_the_one_instance_cycle_passes_once_and_its_record_names_its_store(tmp_path: Path) -> None:
    """One store, one queue, one approval: the run passes once (a guard, criterion
    C), and the record it leaves names its store (new with design 1.4)."""
    deployment = Deployment(
        tmp_path, store=InMemoryStateStore(), transport=InMemoryHitlTransport(),
        bindings=eh._Bindings(),
    )
    started = deployment.start()
    assert isinstance(started, WorkflowSuspended)
    deployment.approve(started.event_key)
    outcome: Any = deployment.resume()
    assert isinstance(outcome, (WorkflowSuspended, WorkflowCompleted)), outcome
    assert downstream_runs(deployment.bindings) == 1
    identity = getattr(deployment.store, "identity", None)
    assert identity is not None, "the store declares no identity"
    assert deployment.record().model_dump().get("state_store_identity") == identity
