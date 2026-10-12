# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A writer outside the engine can make the step after an approved gate run again: disclosed and measured (decision 1).

Lane ``378j-fixup`` item L, lane ``378i-d2ext``'s F-B. Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation
(``D-IMPL-378``), decision 1, verbatim: *"(a) Disclose the rewind. The outside writer can already rerun the step."*
SEC-001 stays OPEN: this module measures, it closes nothing.

The engine is the only writer of a workflow record the SDK supports (the single-writer trust model). A writer outside
it, here ``src/ccf/controlplane/state.py::AuditedStateWriter`` used directly (a single-writer violation), can still
write the record. Each test runs the two-gate workflow past its first gate on a real approval, so the step after that
gate (``archive-certificates``) runs once and the run suspends at its second gate; then the outside writer rewrites the
record, and the tests measure what a resumption does with it (lane ``378i-d2ext``'s probes
``probe_outside_writer_suspended_record.py`` and ``probe_outside_writer_exception_routed.py``, measured on
``9a37ccb``; re-measured by lane ``378j-fixup`` on code identical to ``dl-378-integ`` @ ``6cd6023e``):

* **the rewind**: the record rewritten to ``suspended`` at the first gate, its suspension's trace entry restamped, so
  no approval request, verdict or closure names the rewound suspension. A resumption finds no approval for it and
  restores its missing request (decision 8 (a)); one human approval of that request then runs the step after the gate
  a second time;
* **the exception-routed write**: the record rewritten to ``exception-routed`` at the step after the gate. A
  resumption retries the routed node through the engine's exception-routed branch
  (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``): the step runs a second time, and no human
  verdict is recorded.

So the recovery gives the outside writer no rerun it did not already have, and its rerun needs a human approval the
exception-routed write does not. Asserted as the measured state, never as an expected failure. Test vocabulary only
(CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ccf.controlplane.audit import AuditEvent
from ccf.controlplane.state import AuditedStateWriter
from ccf_runtime.workflow.engine import WorkflowSuspended
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from tests.workflow import test_engine as eh
from tests.workflow.test_restore_missing_approval_request import (
    APPROVER,
    DOWNSTREAM,
    EXECUTION,
    FIRST_GATE,
    Run,
    compose,
    requests,
    resume,
    start,
    state_of,
)

#: The instant the outside writer stamps its write with.
_OUTSIDE = datetime(2030, 1, 1, tzinfo=UTC)


def _past_the_first_gate(run: Run) -> WorkflowStateRecord:
    """Start, approve the first gate, resume: the step after it runs once and the run suspends at its second gate."""
    first = start(run)
    assert isinstance(first, WorkflowSuspended) and first.gate == FIRST_GATE, first
    eh._resolve_gate(
        run.registry, run.transport, tenant=run.tenant, event_key=first.event_key, action="approve", subject_id=APPROVER
    )
    second = resume(run)
    assert isinstance(second, WorkflowSuspended) and second.gate != FIRST_GATE, second
    assert run.bindings.ran.count(f"skill:{DOWNSTREAM}") == 1, run.bindings.ran
    return state_of(run)


def _write_outside_the_engine(run: Run, record: WorkflowStateRecord) -> None:
    """The record written through the audited writer directly, not the engine: a single-writer violation."""
    AuditedStateWriter(store=run.registry.state_store, audit=run.registry.audit_log).write(
        eh.execute_as(run.workflow), WORKFLOW_STATE, record, record_id=EXECUTION,
        event=AuditEvent(
            sequence=0, action="state_written", key=run.key, version=run.workflow.identity.definition_hash,
            resolved=True, occurred_at=_OUTSIDE,
        ),
    )


def test_limitation_an_outside_writers_rewind_to_a_passed_gate_reruns_the_next_step_on_one_human_approval(
    tmp_path: Path,
) -> None:
    """The rewound suspension gets its request back; one human approval of it runs the step after the gate again."""
    run = compose(tmp_path)
    real = _past_the_first_gate(run)
    first_suspension = next(index for index, entry in enumerate(real.trace) if entry.kind == "suspend")
    rewound_trace = real.trace[:first_suspension] + (
        real.trace[first_suspension].model_copy(update={"occurred_at": _OUTSIDE}),
    )
    _write_outside_the_engine(
        run, real.model_copy(update={"current_state": FIRST_GATE, "status": "suspended", "trace": rewound_trace})
    )
    assert requests(run, FIRST_GATE) == [], "the rewound suspension must start with no approval request"
    restored = resume(run)
    assert isinstance(restored, WorkflowSuspended) and restored.gate == FIRST_GATE, restored
    assert len(requests(run, FIRST_GATE)) == 1, "the recovery must file one request for the rewound suspension"
    assert run.bindings.ran.count(f"skill:{DOWNSTREAM}") == 1, "a step ran during the recovery"
    eh._resolve_gate(
        run.registry, run.transport, tenant=run.tenant, event_key=run.event_key(FIRST_GATE),
        action="approve", subject_id=APPROVER,
    )
    again = resume(run)
    assert isinstance(again, WorkflowSuspended) and again.gate != FIRST_GATE, again
    assert run.bindings.ran.count(f"skill:{DOWNSTREAM}") == 2, (
        f"the step after the rewound gate ran {run.bindings.ran.count(f'skill:{DOWNSTREAM}')} times, not twice:"
        " the limitation this module measures has moved; change the security how-to (section 4.13) with it"
    )


def test_limitation_the_same_outside_writer_reruns_that_step_with_no_human_through_the_exception_routed_branch(
    tmp_path: Path,
) -> None:
    """Written ``exception-routed`` at the step after the gate, a resumption runs that step again with no human verdict."""
    run = compose(tmp_path)
    real = _past_the_first_gate(run)
    verdicts = len(run.transport.submissions(tenant=run.tenant))
    _write_outside_the_engine(run, real.model_copy(update={"current_state": DOWNSTREAM, "status": "exception-routed"}))
    outcome = resume(run)
    assert isinstance(outcome, WorkflowSuspended), outcome
    assert run.bindings.ran.count(f"skill:{DOWNSTREAM}") == 2, (
        f"the exception-routed resumption ran the step {run.bindings.ran.count(f'skill:{DOWNSTREAM}')} times in all,"
        " not twice: the limitation this module measures has moved; change the security how-to (section 4.13) with it"
    )
    assert len(run.transport.submissions(tenant=run.tenant)) == verdicts, "a human verdict was recorded for the rerun"
