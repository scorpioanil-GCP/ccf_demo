# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""An ineligible principal cannot wedge an approval gate (security close-out, map B item 3).

SEC-001-adjacent (f), ``D-GATE-357`` (2): two disagreeing verdicts on one
suspension refuse every resumption, and no primitive reopens the gate. On a
transport constructed without a Control Plane, the transport judged no
eligibility, so any holder of ``HitlSubmit`` for the event, eligible or not,
could record the opposite verdict and hold the gate for good: a denial of
service by a principal who can never authorize passage. The recorded
acceptance: *"An ineligible opposite verdict is refused at submit and the gate
passes on the eligible approval."* Dave's GO of 2026-10-12 08:45 MST, step 1:
*"enforce eligibility on supported approval transports"*.

**What changed, and what did not.** A :class:`~ccf_runtime.workflow.engine
.WorkflowEngine` now binds its own Control Plane into the transport it composes
(``InMemoryHitlTransport.bind_approver_eligibility``), and refuses at
construction a transport that offers no such binding. The transport then judges
an approval-gate verdict at ``submit`` with the same
:func:`~ccf.hitl.transport.check_approver_eligibility` it applies when it was
constructed with a Control Plane, before attestation, and records nothing when
it refuses. The conflict population
(``WorkflowEngine._recorded_gate_verdicts``) is NOT narrowed: ``D-IMPL-366`` H2
and ``D-IMPL-357`` A4 stand as ruled. A verdict recorded while no event was
under its key is still recorded unjudged and still counts as a conflict
(``tests/workflow/test_sec006_engine_controls.py::test_t12b_a_missing_state_verdict_still_counts_as_a_conflict``).

The first test here is the former
``test_an_ineligible_principals_opposite_verdict_still_holds_the_gate``,
inverted as the acceptance records and renamed to say the new behavior. Test
vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import InMemoryStateStore
from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowWiringError,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.hitl.sec006_harness import expect_eligibility_refusal, submit_as
from tests.workflow import test_engine as eh

EXECUTION = "exec-g"
OFFICER = "officer-1"
OUTSIDER = "outsider-9"
#: The construction refusal's own phrase (``WorkflowEngine.__init__``).
NO_ELIGIBILITY_BINDING = "offers no bind_approver_eligibility"


def _plane() -> ControlPlaneRegistry:
    registry = ControlPlaneRegistry(clock=eh._ticking_clock())
    eh._register_covenant_closure(registry)
    eh._register_refresh_closure(registry)
    return registry


def test_an_ineligible_principals_opposite_verdict_is_refused_at_submit(
    tmp_path: Path,
) -> None:
    """The transport was constructed WITHOUT a Control Plane, as the suite's
    HTTP fixture composes it; the engine it was composed into bound its own.
    ``officer-1`` approves. ``outsider-9``, neither eligible nor the starter,
    presents the opposite verdict: it is refused by the ruled typed refusal and
    nothing is recorded, so it cannot hold the gate."""
    registry = _plane()
    engine, transport, workflow, event_key, bound = eh._suspended_covenant(
        registry, tmp_path, execution_id=EXECUTION
    )
    tenant = workflow.definition.tenant
    eh._submit_only(
        transport, tenant=tenant, event_key=event_key, product_content_hash=bound,
        action="approve", subject_id=OFFICER,
    )
    before = transport.submissions(tenant=tenant)
    pending_before = transport.pending(tenant=tenant)

    expect_eligibility_refusal(
        lambda: eh._submit_only(
            transport, tenant=tenant, event_key=event_key, product_content_hash=bound,
            action="reject", subject_id=OUTSIDER,
        ),
        site="transport.submit on an engine-composed transport built without a Control Plane",
    )
    assert transport.submissions(tenant=tenant) == before, (
        "the refused verdict was recorded: a refused submission introduces no state"
        " mutation (D-IMPL-366 ordering ruling)"
    )
    assert transport.pending(tenant=tenant) == pending_before


@pytest.mark.parametrize("ineligible_first", [True, False], ids=["outsider-first", "officer-first"])
def test_the_eligible_approval_passes_the_gate_after_the_ineligible_verdict_is_refused(
    tmp_path: Path, ineligible_first: bool
) -> None:
    """The gate passes on the eligible approval, in either arrival order. The
    outsider-first order is the one an attacker chooses: a verdict parked before
    any officer acts."""
    registry = _plane()
    engine, transport, workflow, event_key, bound = eh._suspended_covenant(
        registry, tmp_path, execution_id=EXECUTION
    )
    tenant = workflow.definition.tenant

    def officer() -> None:
        eh._submit_only(
            transport, tenant=tenant, event_key=event_key, product_content_hash=bound,
            action="approve", subject_id=OFFICER,
        )

    def outsider() -> None:
        expect_eligibility_refusal(
            lambda: eh._submit_only(
                transport, tenant=tenant, event_key=event_key, product_content_hash=bound,
                action="reject", subject_id=OUTSIDER,
            ),
            site="transport.submit (the outsider's opposite verdict)",
        )

    for step in (outsider, officer) if ineligible_first else (officer, outsider):
        step()
    recorded = transport.submissions(tenant=tenant)
    assert [(s.principal.approver.subject_id, s.action) for s in recorded] == [(OFFICER, "approve")]

    outcome = asyncio.run(
        engine.resume(
            eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision="approved"
        )
    )
    assert isinstance(outcome, WorkflowCompleted), (
        f"the gate did not pass on the eligible approval (outcome: {outcome!r})"
    )
    assert outcome.terminal_state == "approved"
    record = registry.state_store.get(WORKFLOW_STATE, f"{tenant}/{EXECUTION}")
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "terminal"


class _TransportWithoutEligibilityBinding:
    """The whole :class:`~ccf.hitl.transport.HITLTransportProtocol`, delegated
    to the reference transport, and no ``bind_approver_eligibility``: the shape
    of a third-party transport the engine cannot make judge eligibility."""

    scope = "process"

    def __init__(self) -> None:
        self._inner = InMemoryHitlTransport()

    def enqueue(self, **kwargs: Any) -> Any:
        return self._inner.enqueue(**kwargs)

    def dequeue(self, **kwargs: Any) -> Any:
        return self._inner.dequeue(**kwargs)

    def pending(self, **kwargs: Any) -> Any:
        return self._inner.pending(**kwargs)

    def remove(self, **kwargs: Any) -> Any:
        return self._inner.remove(**kwargs)

    def view(self, authorized: Any) -> Any:
        return self._inner.view(authorized)

    def submit(self, authorized: Any, **kwargs: Any) -> Any:
        return self._inner.submit(authorized, **kwargs)

    def submissions(self, **kwargs: Any) -> Any:
        return self._inner.submissions(**kwargs)

    def close_gate(self, authorized: Any, **kwargs: Any) -> Any:
        return self._inner.close_gate(authorized, **kwargs)

    def closures(self, **kwargs: Any) -> Any:
        return self._inner.closures(**kwargs)


def test_an_engine_refuses_a_transport_it_cannot_bind_for_eligibility(tmp_path: Path) -> None:
    """Enforced, not assumed: a transport that cannot take the engine's Control
    Plane as its eligibility judge is refused at construction, by name, before
    any execution runs."""
    registry = ControlPlaneRegistry(clock=eh._ticking_clock(), state_store=InMemoryStateStore())
    with pytest.raises(WorkflowWiringError, match=NO_ELIGIBILITY_BINDING):
        eh._engine(registry, tmp_path, transport=_TransportWithoutEligibilityBinding())


def test_a_transport_no_engine_composed_still_judges_nothing() -> None:
    """The narrowness control. A transport built without a Control Plane and
    composed into no workflow engine keeps the pre-composition posture
    (``check_approver_eligibility``: an unbound plane performs no check): a
    door-shaped verdict by a principal the event's policy does not admit is
    recorded. The binding is the engine's act, so primitives used alone are
    unchanged."""
    transport = InMemoryHitlTransport()
    event = PendingHitlEvent(
        event_key="standalone-gate-1",
        event_class="approval-gate",
        tenant="acme-bank",
        workflow_state_ref="acme-bank/standalone",
        product_content_hash="c" * 64,
        policy_ref="ccf-artifact://acme-bank/approval-policy/credit-officer@1.0.0",
        requested_by="workflow-tests",
    )
    transport.enqueue(event=event)
    recorded = submit_as(transport, event, subject_id=OUTSIDER, action="reject")
    assert recorded.event_state_at_submit == "pending"
    assert transport.submissions(tenant="acme-bank") == (recorded,)


def test_rebuilding_an_engine_over_the_same_transport_and_plane_is_admitted(tmp_path: Path) -> None:
    """Positive control: binding the same plane twice is idempotent, so the
    ordinary product path that rebuilds engines over one pair still builds."""
    registry = ControlPlaneRegistry(clock=eh._ticking_clock(), state_store=InMemoryStateStore())
    transport = InMemoryHitlTransport()
    first, _, _ = eh._engine(registry, tmp_path / "a", transport=transport)
    second, _, _ = eh._engine(registry, tmp_path / "b", transport=transport)
    assert isinstance(first, WorkflowEngine) and isinstance(second, WorkflowEngine)


def test_every_engine_plane_bound_to_one_transport_must_admit_the_verdict(tmp_path: Path) -> None:
    """Fail-closed across planes: a transport composed into two engines judges a
    verdict against BOTH engines' Control Planes. Here the second plane, over the
    same state store, holds no approval policy at all, so even ``officer-1``,
    whom the first plane's policy admits, is refused, and nothing is recorded.
    Replicas of one deployment register the same policies and judge alike
    (``tests/workflow/test_approval_gate_limits.py`` runs two such engines over
    one transport)."""
    store = InMemoryStateStore()
    first = ControlPlaneRegistry(clock=eh._ticking_clock(), state_store=store)
    eh._register_covenant_closure(first)
    eh._register_refresh_closure(first)
    engine, transport, _ = eh._engine(first, tmp_path / "a")
    eh._engine(
        ControlPlaneRegistry(clock=eh._ticking_clock(), state_store=store),
        tmp_path / "b",
        transport=transport,
    )
    workflow = eh._covenant(first)
    suspended = asyncio.run(engine.execute(eh.execute_as(workflow), workflow, execution_id=EXECUTION))
    tenant = workflow.definition.tenant
    pending = next(e for e in transport.pending(tenant=tenant) if e.event_key == suspended.event_key)
    expect_eligibility_refusal(
        lambda: submit_as(transport, pending, subject_id=OFFICER),
        site="transport.submit judged by a second engine's plane that admits no one",
    )
    assert transport.submissions(tenant=tenant) == ()


def test_the_transports_verdict_vocabulary_is_the_gates() -> None:
    """The transport spells the two verdicts itself (an import cycle forbids
    importing them); this pins its spelling to the gate primitive's."""
    from ccf.hitl import transport as transport_module
    from ccf.hitl.approval_gate import GATE_ACTIONS

    assert transport_module._GATE_VERDICTS == GATE_ACTIONS
