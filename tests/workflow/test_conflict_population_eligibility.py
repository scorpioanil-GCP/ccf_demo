"""The conflict population is not narrowed by eligibility (D-GATE-357 (3); D-IMPL-366 H2).

A CONTROL, GREEN TODAY: it pins ruled behavior that no test pinned.
``D-IMPL-366`` H2 ruled that the population the conflict refusal runs over
(``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._recorded_gate_verdicts``)
"is not narrowed", and ``D-IMPL-357`` A4 widened it to every recorded gate
verdict on the suspension, "eligible or not". ``D-GATE-357`` (3) carried that
the narrowing was unproven, and ``D-IMPL-366`` carried that it was pinned only
on the missing-state axis (A5). Lane 378-approval measured it: a severing that
drops verdicts by principals the gate's policy does not admit, keeping every
missing-state verdict, turned none of 778 tests in ``tests/workflow``,
``tests/hitl`` and ``tests/http_api`` red.

This test turns that severing red. On an UNBOUND transport (no Control Plane,
as the suite's HTTP fixture and the local CLI compose it), the transport judges
no eligibility, so a principal outside the gate's policy can record a verdict.
``officer-1`` approves; ``outsider-9``, who is neither eligible nor the
starter, records a rejection of the same suspension. The resumption must
refuse for the conflict: a verdict that can never authorize passage still
holds the gate for a human to reconcile. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.workflow.engine import WorkflowResumeRefused
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.workflow import test_engine as eh

EXECUTION = "exec-g"
OUTSIDER = "outsider-9"
#: The conflict refusal's own phrase
#: (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``).
CONFLICT = "carries conflicting human verdicts"


def test_an_ineligible_principals_opposite_verdict_still_holds_the_gate(
    tmp_path: Path,
) -> None:
    registry = ControlPlaneRegistry(clock=eh._ticking_clock())
    eh._register_covenant_closure(registry)
    eh._register_refresh_closure(registry)
    engine, transport, workflow, event_key, bound = eh._suspended_covenant(
        registry, tmp_path, execution_id=EXECUTION
    )
    tenant = workflow.definition.tenant
    eh._submit_only(
        transport, tenant=tenant, event_key=event_key, product_content_hash=bound,
        action="approve", subject_id="officer-1",
    )
    rejection = eh._submit_only(
        transport, tenant=tenant, event_key=event_key, product_content_hash=bound,
        action="reject", subject_id=OUTSIDER,
    )
    # The rejection is recorded against the open gate, and its principal is
    # outside the gate's policy: it can never be the authority.
    assert rejection.event_state_at_submit == "pending"
    assert rejection.approval_policy_ref is not None

    outcome = asyncio.run(
        engine.resume(
            eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision="approved"
        )
    )
    assert isinstance(outcome, WorkflowResumeRefused), (
        "the conflict population was narrowed by eligibility: an ineligible"
        " principal's opposite verdict no longer holds the gate"
        f" (outcome: {outcome!r})"
    )
    assert CONFLICT in outcome.reason, outcome.reason
    record = registry.state_store.get(WORKFLOW_STATE, f"{tenant}/{EXECUTION}")
    assert isinstance(record, WorkflowStateRecord)
    assert record.status == "suspended"
