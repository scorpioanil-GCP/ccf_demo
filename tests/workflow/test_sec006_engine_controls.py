"""SEC-006 — approver eligibility at the engine, the factory and the requester stamp (`D-IMPL-366`).

RED-FIRST on `main` @ `a236e6ce`, the `D-IMPL-363` shape: each control is written
to the RULED surface and fails today for one named reason — **MISSING
CONTRACT** (a ruled name the tree lacks) or **BEHAVIORAL** (the tree admits
what must be refused, or refuses what must be admitted). Nothing fails at
import, collection or fixture setup.

Sites covered here, by the brief's §5 row names: **S3** (``_gate_authority``,
T4/T4b), **S4** (the factory, T5), **S5** (the requester stamp, T6), **M**
(the missing state, T12/T12b — the H2 requirement) and **E** (the escalation
pin, T13). Row **A** — the four existing SEC-001 controls — is re-run from
:mod:`tests.workflow.test_engine`, not duplicated here.

**Why these tests use the TWO-GATE fixture and a typed policy, not the covenant
fixture as shipped.** T5 rules that a workflow whose gate names a
``DeclaredArtifact`` approval policy fails construction once the repair lands,
which makes the covenant fixture AS REGISTERED unconstructible afterwards.
Controls that must be GREEN after the repair without being rewritten therefore
bind a typed ``ccf.approval-policy`` — registered by the test, never written
into a fixture (it is not manifest-addressable, RULED) — either through the
two-gate fixture pair added beside the historical fixtures (``tasks/
two_gate_release_task.yaml``, ``workflows/two_gate_release_workflow.yaml``)
or through a ``gate_policies`` mutation of the covenant definition, which
registers under a NEW key and leaves the fixture's own key untouched. Every
such test is MISSING CONTRACT today at the typed registration, by construction.

Harness reuse (Dave's GO): :mod:`tests.workflow.test_engine` is imported as a
namespace for its composition helpers — never its test functions. No existing
test or fixture is modified.

Test vocabulary only (CINV-01): ``alice``, ``bob``, ``carol`` and the
``officer-N`` subjects name no real principal.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.approval_gate import ApprovalGate, GateResolution
from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
from ccf.workflow.factory import Workflow, WorkflowConstructionError
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowExceptionRouted,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.composition import register_versioned_at_composition
from tests.hitl.capabilities import submit_capability
from tests.hitl.sec006_harness import (
    execute_as_principal,
    expect_eligibility_refusal,
    field,
    plain_hitl_plane,
    register_typed_policy,
    resume_as_principal,
    submit_as,
)
from tests.workflow import test_engine as eh

TYPED_POLICY_KEY = "acme-bank/approval-policy/sec006-officers"
TWO_GATE_WORKFLOW = "workflows/two_gate_release_workflow.yaml"
TWO_GATE_TASK = "tasks/two_gate_release_task.yaml"
COVENANT_WORKFLOW = "workflows/covenant_review_workflow.yaml"
COVENANT_GATE = "credit-officer-approval"


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    """This module's own plane: the two shipped closures, nothing else. The
    two-gate task's skills are the certificate-refresh task's own two skill
    artifacts, already registered by that closure — not re-registered here."""
    plane = ControlPlaneRegistry(clock=eh._ticking_clock())
    eh._register_covenant_closure(plane)
    eh._register_refresh_closure(plane)
    return plane


# --- composition helpers --------------------------------------------------------


def _typed_policy(registry: ControlPlaneRegistry, eligible: frozenset[str]) -> str:
    """The RULED policy, registered first — the MISSING CONTRACT every engine
    control but T5 reports today (``ccf.hitl.APPROVAL_POLICY``)."""
    return register_typed_policy(registry, TYPED_POLICY_KEY, eligible=eligible)


def _two_gate(registry: ControlPlaneRegistry, *, eligible: frozenset[str]) -> Workflow:
    """The two-gate release workflow over the typed policy both gates pin."""
    _typed_policy(registry, eligible)
    task_fixture = eh._load(TWO_GATE_TASK)
    task = parse_artifact(task_fixture["task_definition"], eh.TASK_DEFINITION)
    workflow_fixture = eh._load(TWO_GATE_WORKFLOW)
    version = register_versioned_at_composition(
        registry, workflow_fixture["keys"]["task_definition"], task, eh.TASK_DEFINITION
    )
    assert isinstance(version, str), version
    return eh._construct(registry, TWO_GATE_WORKFLOW)


def _typed_covenant(registry: ControlPlaneRegistry, *, eligible: frozenset[str]) -> Workflow:
    """The covenant definition with its ONE gate rebound to the typed policy —
    a mutation, so it registers under a new key and the fixture's own
    DeclaredArtifact-gated key stays exactly as shipped."""
    typed_uri = _typed_policy(registry, eligible)
    return eh._construct(registry, COVENANT_WORKFLOW, gate_policies={COVENANT_GATE: typed_uri})


def _pending(transport: InMemoryHitlTransport, *, tenant: str, event_key: str) -> PendingHitlEvent:
    return next(e for e in transport.pending(tenant=tenant) if e.event_key == event_key)


def _state(registry: ControlPlaneRegistry, *, tenant: str, execution_id: str) -> WorkflowStateRecord:
    record = registry.state_store.get(WORKFLOW_STATE, f"{tenant}/{execution_id}")
    assert isinstance(record, WorkflowStateRecord)
    return record


def _run(coroutine: Any) -> Any:
    return asyncio.run(coroutine)


def _suspend_two_gate(
    registry: ControlPlaneRegistry,
    tmp_path: Path,
    *,
    eligible: frozenset[str],
    starter: str | None = None,
    transport: InMemoryHitlTransport | None = None,
    execution_id: str = "exec",
) -> tuple[WorkflowEngine, InMemoryHitlTransport, Workflow, PendingHitlEvent]:
    """Start the two-gate workflow (as ``starter`` when named, else as the
    shared test principal) and suspend it on ``first-approval``."""
    workflow = _two_gate(registry, eligible=eligible)
    engine, transport, _ = eh._engine(registry, tmp_path, transport=transport)
    tenant = workflow.definition.tenant
    capability = (
        eh.execute_as(workflow)
        if starter is None
        else execute_as_principal(tenant=tenant, resource=workflow.definition_key, principal=starter)
    )
    suspended = _run(engine.execute(capability, workflow, execution_id=execution_id))
    assert isinstance(suspended, WorkflowSuspended) and suspended.gate == "first-approval"
    return engine, transport, workflow, _pending(transport, tenant=tenant, event_key=suspended.event_key)


# --- S4: the factory fails closed (T5) ---------------------------------------------


def test_t5_a_declared_artifact_gate_policy_is_refused_at_construction(
    registry: ControlPlaneRegistry,
) -> None:
    """S4, T5 — BEHAVIORAL today.

    The covenant fixture's ``credit-officer-approval`` gate pins a
    ``DeclaredArtifact`` approval policy — the pre-change shape every fixture
    registers. The factory class-checks each routed ``gate_policies`` target
    against ``ccf.approval-policy`` and refuses by name (brief §4 (5); the
    task-ref precedent). Today the workflow constructs.
    """
    # The AS-SHIPPED closure: the fixture's own DeclaredArtifact approval policy
    # under the key the gate pins (the shared closure now registers the typed
    # policy there, so this control builds the pre-change shape explicitly).
    plane = ControlPlaneRegistry(clock=eh._ticking_clock())
    eh._register_covenant_closure(plane, as_shipped=True)
    eh._register_refresh_closure(plane)
    try:
        workflow = eh._covenant(plane)
    except WorkflowConstructionError:
        return
    pytest.fail(
        "BEHAVIORAL: WorkflowFactory CONSTRUCTED a workflow whose gate policy is a"
        " DeclaredArtifact, not a typed ccf.approval-policy; the factory must"
        f" refuse by name (D-IMPL-366; brief §4 (5)): {workflow.definition_key!r}"
    )


# --- S3: the engine is the backstop (T4, T4b) ---------------------------------------


def test_t4_an_ineligible_verdict_through_an_unbound_transport_does_not_resume(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """S3, T4 (ineligible) — MISSING CONTRACT today.

    The transport is UNBOUND, so S1 cannot fire; the submission is door-shaped,
    so S2 is not used. ``_gate_authority``, judging against
    ``gate_policies[gate]`` and ``record.started_by``, excludes a verdict from a
    principal outside the policy, and the resume is refused (brief §5, S3).
    """
    engine, transport, workflow, event = _suspend_two_gate(
        registry, tmp_path, eligible=frozenset({"officer-a", "officer-b"}), starter="officer-a"
    )
    submit_as(transport, event, subject_id="outsider-1")  # unbound: lands
    assert len(transport.submissions(tenant=event.tenant)) == 1
    outcome = _run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id="exec", decision="archive-certificates")
    )
    assert isinstance(outcome, WorkflowResumeRefused), (
        f"BEHAVIORAL: the engine resumed on an INELIGIBLE verdict: {outcome!r}"
    )
    assert _state(registry, tenant=event.tenant, execution_id="exec").status == "suspended"


def test_t4_a_self_verdict_through_an_unbound_transport_does_not_resume(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """S3, T4 (self-approval) — MISSING CONTRACT today.

    The starter ``officer-a`` is eligible AND is ``record.started_by``; their
    own door approval, recorded through an unbound transport, is not
    authority (requester ≠ approver, unconditional when a policy is bound).
    """
    engine, transport, workflow, event = _suspend_two_gate(
        registry, tmp_path, eligible=frozenset({"officer-a", "officer-b"}), starter="officer-a"
    )
    submit_as(transport, event, subject_id="officer-a")
    outcome = _run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id="exec", decision="archive-certificates")
    )
    assert isinstance(outcome, WorkflowResumeRefused), (
        f"BEHAVIORAL: the engine resumed on the STARTER's own verdict: {outcome!r}"
    )


def test_t4b_an_eligible_non_starter_verdict_resumes(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """S3, T4b — the positive control — MISSING CONTRACT today.

    Without this the backstop could be satisfied by an engine that refused
    every gate. ``officer-b`` is eligible and did not start the execution:
    the gate opens on the artifact's route and the execution reaches the
    second gate.
    """
    engine, transport, workflow, event = _suspend_two_gate(
        registry, tmp_path, eligible=frozenset({"officer-a", "officer-b"}), starter="officer-a"
    )
    submit_as(transport, event, subject_id="officer-b")
    outcome = _run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id="exec", decision="archive-certificates")
    )
    assert isinstance(outcome, WorkflowSuspended), f"BEHAVIORAL: an eligible verdict was refused: {outcome!r}"
    assert outcome.gate == "second-approval"


# --- S5: the requester is the starter, across a second gate (T6) ----------------------


def test_t6_a_second_gate_reached_by_a_different_resumer_still_names_the_starter(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """S5, T6 — MISSING CONTRACT today.

    G1 (a): the requester is the STARTER. ``alice`` holds ``Execute`` and starts;
    gate 1 suspends with ``event.requested_by == "alice"`` and
    ``record.started_by == "alice"``; ``bob`` (eligible) approves through the
    primitive; ``carol`` holds ``Resume`` and resumes; gate 2 suspends with
    ``event.requested_by == "alice"`` — asserted on the EVENT, not on any
    refusal — so ``alice``'s approval of gate 2 refuses at S1 (and would at
    S3), while ``carol``, eligible and not the starter, approves gate 2 and
    the resumer is not constrained (brief §9).
    """
    plane_transport = InMemoryHitlTransport(
        control_plane=registry, hitl_policy_key=plain_hitl_plane(registry)
    )
    engine, transport, workflow, event1 = _suspend_two_gate(
        registry,
        tmp_path,
        eligible=frozenset({"alice", "bob", "carol"}),
        starter="alice",
        transport=plane_transport,
    )
    tenant = workflow.definition.tenant
    assert field(event1, "requested_by", ruling="D-IMPL-366 G1 (a)") == "alice"
    record = _state(registry, tenant=tenant, execution_id="exec")
    assert field(record, "started_by", ruling="D-IMPL-366 G1 (a)") == "alice"

    gate = ApprovalGate(
        transport=transport,
        audit=registry.audit_log,
        clock=eh._ticking_clock(),
        control_plane=registry,
        hitl_policy_key=plain_hitl_plane(registry),
    )
    resolution = gate.resolve(
        submit_capability(tenant=tenant, principal="bob", event_key=event1.event_key),
        event_key=event1.event_key,
        action="approve",
        principal=eh._binding(event1.product_content_hash, subject_id="bob"),
    )
    assert isinstance(resolution, GateResolution)

    resumed = _run(
        engine.resume(
            resume_as_principal(tenant=tenant, resource=workflow.definition_key, principal="carol"),
            workflow,
            execution_id="exec",
            decision="archive-certificates",
        )
    )
    assert isinstance(resumed, WorkflowSuspended) and resumed.gate == "second-approval"
    event2 = _pending(transport, tenant=tenant, event_key=resumed.event_key)
    assert field(event2, "requested_by", ruling="D-IMPL-366 G1 (a)") == "alice", (
        "the second gate's requester is not the starter (G1 (a) rules the starter,"
        " not the Resume holder who reached the gate)"
    )
    assert field(_state(registry, tenant=tenant, execution_id="exec"), "started_by", ruling="G1") == "alice"

    expect_eligibility_refusal(
        lambda: submit_as(transport, event2, subject_id="alice"),
        site="S1 transport.submit (the starter approving the second gate)",
    )
    submit_as(transport, event2, subject_id="carol")  # eligible, not the starter: admitted
    completed = _run(
        engine.resume(
            resume_as_principal(tenant=tenant, resource=workflow.definition_key, principal="carol"),
            workflow,
            execution_id="exec",
            decision="released",
        )
    )
    assert isinstance(completed, WorkflowCompleted) and completed.terminal_state == "released"


# --- M: the missing state never becomes authority (T12, T12b; the H2 requirement) ---


class _FailNextSubmit(InMemoryHitlTransport):
    """The reference transport with ONE injected ``submit`` failure, so a real
    primitive's claim → failed submit → rollback re-enqueue path runs exactly
    as :meth:`ApprovalGate.resolve` writes it (the two adjacent statements)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fail_next_submit = False

    def submit(self, authorized: Any, *, submission: Any) -> Any:
        if self.fail_next_submit:
            self.fail_next_submit = False
            raise RuntimeError("injected: the primitive's submit failed after its claim")
        return super().submit(authorized, submission=submission)


def _record_missing_state_approval(
    registry: ControlPlaneRegistry, tmp_path: Path, *, transport: InMemoryHitlTransport
) -> tuple[WorkflowEngine, Workflow, PendingHitlEvent, Any]:
    """Suspend; drain the gate's event with ``dequeue`` (the MISSING state's
    "a ``dequeue`` drained it" row); record an ELIGIBLE officer's door approval
    while nothing is pending or claimed; re-enqueue the event. Returns the
    recorded submission, which must carry ``event_state_at_submit ==
    "missing"`` and must never become authority (RULED, H2)."""
    engine, transport, workflow, event = _suspend_two_gate(
        registry, tmp_path, eligible=frozenset({"officer-5", "officer-6"}), transport=transport
    )
    tenant = workflow.definition.tenant
    drained = transport.dequeue(tenant=tenant)
    assert drained is not None and drained.event_key == event.event_key
    assert transport.pending(tenant=tenant) == ()
    recorded = submit_as(transport, event, subject_id="officer-5")  # unbound: lands, unjudged
    assert field(recorded, "event_state_at_submit", ruling="D-IMPL-366 H2") == "missing"
    transport.enqueue(event=drained)
    return engine, workflow, event, recorded


def test_t12_a_missing_state_submission_is_not_authority_after_the_event_is_enqueued(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """M, T12 (i) — MISSING CONTRACT today.

    Recorded while no event was pending or claimed, the submission is stamped
    ``missing`` and nothing is judged. When the gate's event is then enqueued,
    the engine still refuses: ``_gate_authority`` excludes ``missing``
    unconditionally (brief §4c). Today the unstamped leg would admit it as soon
    as the gate is pending — the premature-approval shape.

    **Severing rule for this control (carried requirement (2), corrected):**
    the ``event_state_at_submit != "missing"`` conjunct and the unstamped leg's
    ``in (None, "pending")`` guard overlap; they are removed TOGETHER for this
    test's required red, and individual removals may remain green.
    """
    engine, workflow, event, _ = _record_missing_state_approval(
        registry, tmp_path, transport=InMemoryHitlTransport()
    )
    outcome = _run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id="exec", decision="archive-certificates")
    )
    assert isinstance(outcome, WorkflowResumeRefused), (
        f"BEHAVIORAL: a missing-state submission became authority after enqueue: {outcome!r}"
    )
    assert _state(registry, tenant=event.tenant, execution_id="exec").status == "suspended"


def test_t12_a_missing_state_submission_is_not_authority_after_a_rollback_re_enqueue(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """M, T12 (ii) — MISSING CONTRACT today.

    A primitive claims the event (``remove``), its ``submit`` fails, and the
    rollback re-enqueues; the earlier ``missing`` submission is STILL not
    authority — the fact lives on the record, and no later enqueue can rewrite
    it (brief §4c, permanence). The failed submit is injected on the reference
    transport so the real primitive runs its own rollback path.
    """
    transport = _FailNextSubmit()
    engine, workflow, event, _ = _record_missing_state_approval(registry, tmp_path, transport=transport)
    tenant = event.tenant
    gate = ApprovalGate(transport=transport, audit=registry.audit_log, clock=eh._ticking_clock())
    transport.fail_next_submit = True
    with pytest.raises(RuntimeError, match="injected"):
        gate.resolve(
            submit_capability(tenant=tenant, principal="officer-6", event_key=event.event_key),
            event_key=event.event_key,
            action="approve",
            principal=eh._binding(event.product_content_hash, subject_id="officer-6"),
        )
    assert _pending(transport, tenant=tenant, event_key=event.event_key) == event  # rolled back
    outcome = _run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id="exec", decision="archive-certificates")
    )
    assert isinstance(outcome, WorkflowResumeRefused), (
        f"BEHAVIORAL: a missing-state submission became authority after a rollback re-enqueue: {outcome!r}"
    )


def test_t12b_a_missing_state_verdict_still_counts_as_a_conflict(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """M, T12b — SEC-001 conflict detection PRESERVED — MISSING CONTRACT today.

    With an opposite, eligible verdict also recorded (``officer-6`` rejects
    while the event is pending), ``resume`` refuses as a CONFLICT: the
    ``missing`` verdict stays in ``_recorded_gate_verdicts``, the broader
    population, which is NOT narrowed (D-IMPL-366 amendment). The reason text
    is the conflict guard's own phrase, and not the route compare's — the
    distinct refusal that pins which guard answered.
    """
    engine, workflow, event, _ = _record_missing_state_approval(
        registry, tmp_path, transport=InMemoryHitlTransport()
    )
    tenant = event.tenant
    engine_transport = engine._hitl_transport  # the same instance the helper returned
    assert engine_transport.pending(tenant=tenant) == (event,)
    submit_as(engine_transport, event, subject_id="officer-6", action="reject")
    outcome = _run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id="exec", decision="archive-certificates")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    assert "carries conflicting human verdicts" in outcome.reason, (
        f"BEHAVIORAL: the missing-state verdict was dropped from the conflict population: {outcome.reason}"
    )
    assert "does not agree with the route" not in outcome.reason


# --- E: the escalation pin (T13) -----------------------------------------------------


def test_t13_escalation_resolution_judges_no_eligibility(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """E, T13 — the pin — MISSING CONTRACT today (the typed policy it composes over).

    ``_escalation_authority`` and ``ExceptionEscalation.resolve`` are NOT
    instrumented (RULED: approval gates only; escalation is the §9 row
    "escalation eligibility", the named follow-on). Over the typed-policy
    covenant, a duty officer who is in NO approval policy resolves the
    escalation and the routed resume proceeds — not refused.
    """
    workflow = _typed_covenant(registry, eligible=frozenset({"officer-1"}))
    engine, transport, bindings = eh._engine(registry, tmp_path, failing=frozenset({"fetch-certificates"}))
    routed = _run(engine.execute(eh.execute_as(workflow), workflow, execution_id="exec-esc"))
    assert isinstance(routed, WorkflowExceptionRouted)
    bindings.failing = frozenset()
    tenant = workflow.definition.tenant
    key = f"{tenant}/exec-esc"
    record = _state(registry, tenant=tenant, execution_id="exec-esc")
    event_key = f"{key}/fetch-certificates"
    escalation = eh._escalate(
        registry, transport, tenant=tenant, key=key, event_key=event_key,
        product_content_hash=content_hash(record),
    )
    eh._resolve_escalation(
        escalation, tenant=tenant, event_key=event_key,
        product_content_hash=content_hash(record), subject_id="duty-officer-9",
    )
    outcome = _run(engine.resume(eh.resume_as(workflow), workflow, execution_id="exec-esc", decision="retry"))
    assert not isinstance(outcome, WorkflowResumeRefused), (
        f"BEHAVIORAL: an escalation resolution was judged for approver eligibility: {outcome.reason}"
    )
    assert isinstance(outcome, WorkflowSuspended)  # retried, reached the (typed-policy) gate
