"""A gate approved through the submit-only door whose passage commit then failed stays stuck: disclosed (decision 3).

Lane ``378j-fixup`` item M, lane ``378i-d2ext``'s F-A (pre-existing: measured on ``a539c215`` and ``86cac0b`` by that
lane, and by lane ``378j-fixup`` on code identical to ``dl-378-integ`` @ ``6cd6023e``). Dave, 2026-10-09 16:38 MST,
adopting Grok's recommendation (``D-IMPL-378``), decision 3, verbatim: *"Disclose the stuck door-approved gate."*
SEC-001 stays OPEN: this module measures, it closes nothing.

A resumption whose passage commit never landed is retried on its own closure and runs the step after the gate once,
as ``tests/workflow/test_approval_gate_limits.py::test_a_passage_whose_commit_never_landed_is_retried_once_on_its_own_closure``
measures for an approval resolved through the gate primitive (``src/ccf/hitl/approval_gate.py::ApprovalGate``, a
stamped verdict). An approval recorded through the submit-only action door instead (``POST /hitl/actions``, which
calls ``InMemoryHitlTransport.submit``; D-IMPL-62) carries no stamp and is recorded while its request is pending. When
that passage's commit fails, its closure has retired the request, and the engine counts an unstamped approval only
while its request is still pending (code reading of
``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority``), so every later resumption, from either
process, is refused for want of an approval, and the step after the gate never runs. Asserted as the measured state,
never as an expected failure: the run is left for an operator. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.workflow.engine import WorkflowResumeRefused, WorkflowSuspended
from tests.hitl.sec006_harness import execute_as_principal
from tests.workflow import test_engine as eh
from tests.workflow.test_approval_gate_limits import FIRST_GATE, state_of, two_processes, workflow_write
from tests.workflow.test_resume_single_flight import APPROVER, DOWNSTREAM, EXECUTION, STARTER, resume

#: The refusal a resumption meets at a gate no counted approval opens
#: (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``).
_NO_APPROVAL = "no approval for this suspension has returned through the HITL authority path"


def test_limitation_a_door_approved_gate_whose_passage_commit_failed_is_refused_from_every_process_and_never_passes(
    tmp_path: Path,
) -> None:
    """The door's approval, the commit failing at the storage layer: both processes refused, the step never run."""
    bindings = eh._Bindings()
    transport = InMemoryHitlTransport()
    a, b, records = two_processes(tmp_path, bindings, transport)
    tenant = a.workflow.definition.tenant
    starter = execute_as_principal(tenant=tenant, resource=a.workflow.definition_key, principal=STARTER)
    suspended = asyncio.run(a.engine.execute(starter, a.workflow, execution_id=EXECUTION))
    assert isinstance(suspended, WorkflowSuspended) and suspended.gate == FIRST_GATE, suspended
    bound = next(e.product_content_hash for e in transport.pending(tenant=tenant) if e.event_key == suspended.event_key)
    recorded = eh._submit_only(
        transport, tenant=tenant, event_key=suspended.event_key, product_content_hash=bound,
        action="approve", subject_id=APPROVER,
    )
    assert (recorded.event_state_at_submit, recorded.answered_event_class) == ("pending", None), (
        f"not the door's unstamped approval, recorded while its request was pending: {recorded!r}"
    )
    records.arm_failure(workflow_write)
    with pytest.raises(RuntimeError, match="state store unavailable"):
        asyncio.run(resume(a.engine, a.workflow))
    key = f"{tenant}/{EXECUTION}"
    record = state_of(a.registry, key)
    assert (record.status, record.current_state) == ("suspended", FIRST_GATE), record
    assert len(transport.closures(tenant=tenant)) == 1, "the failed passage's closure is not on the transport"
    assert len(transport.pending(tenant=tenant)) == 0, "the closure did not retire the gate's request"
    for name, process in (("A", a), ("B", b)):
        outcome = asyncio.run(resume(process.engine, process.workflow))
        assert isinstance(outcome, WorkflowResumeRefused), (
            f"[{name}] the retry was not refused: {outcome!r}; the limitation this module measures has moved, so"
            " change the security how-to (section 4.13) with it"
        )
        assert _NO_APPROVAL in outcome.reason, f"[{name}] refused for another reason: {outcome.reason}"
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 0, "the step after the gate ran"
    assert state_of(a.registry, key).status == "suspended"
