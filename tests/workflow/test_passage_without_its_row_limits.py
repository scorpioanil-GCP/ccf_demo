# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Nothing reports a passage committed without its audit row (D-IMPL-378, decision 7 (b); the controls register's write_if row).

A resumption commits its passage through
``src/ccf/controlplane/state.py::AuditedStateWriter.write_if``: the state
store's conditional write, THEN the audit log's append of the attributed
``workflow_resumed`` row. These are two writes. An append that fails after the
commit landed leaves the execution past its gate with no row
(``tests/workflow/test_passage_commit_two_writes_limits.py``). Dave ruled on
decision 7 (06:06 MST, confirmed 06:21 on 2026-10-09): *"(b), with the
documentation correction now. Make a committed transition without its audit row
detectable and recoverable. Do not claim atomicity that does not exist."* At
10:54 MST he chose that design's shape (design 1.5): *"Build after 1.4. Recover
the owed row and leave the stuck run to an operator. Cover grant writes.
Callers get 503 audit-row-owed."* It is not built.

The findings brief's §1.6 asked the controls register to disclose this window
beside its row for ``write_if``. "Nothing reports it" is a claim about absence,
so it is measured here as a comparison with a control: the same passage,
committed WITH its row and interrupted at the same point (the step after the
gate never finished). The failing call raises only the audit log's own error,
and afterwards the SDK's answers about the execution are the same in both: the
state record, a later resumption's refusal, and that refusal's row. The two
audit logs differ by exactly the missing row.

A limit as it stands, not a fix: the design that makes such a passage
detectable turns this test red, and the register's row must change with it.
Composition reuses ``tests/workflow/test_resume_single_flight.py`` and
``tests/workflow/test_passage_commit_two_writes_limits.py``. Test vocabulary
only (CINV-01).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.workflow.engine import WorkflowResumeRefused
from tests.workflow import test_engine as eh
from tests.workflow.test_approval_gate_limits import state_of
from tests.workflow.test_passage_commit_two_writes_limits import _registry, _ResumedRowFails
from tests.workflow.test_resume_single_flight import (
    APPROVER,
    DOWNSTREAM,
    EXECUTION,
    INTERRUPTED,
    BlockingOnceBindings,
    approved_suspension,
    resume,
)


class _RowAppendFails(_ResumedRowFails):
    """The two-writes module's stand-in, keeping the error it raised so the test can name it."""

    def __init__(self) -> None:
        super().__init__()
        self.raised: list[OSError] = []

    def append(self, **kwargs: Any) -> AuditEvent:
        try:
            return super().append(**kwargs)
        except OSError as error:
            self.raised.append(error)
            raise


def events_for(registry: ControlPlaneRegistry, key: str) -> list[AuditEvent]:
    return [event for event in registry.audit_log.events() if event.key == key]


def comparable(event: AuditEvent) -> dict[str, object]:
    """Every field of a row but the two the log and the clock assign: its sequence and its time."""
    return {"type": type(event).__name__, **event.model_dump(mode="json", exclude={"sequence", "occurred_at"})}


def test_limit_nothing_reports_a_passage_whose_row_append_failed(tmp_path: Path) -> None:
    # The window: the passage commit lands and the append of its row fails.
    audit = _RowAppendFails()
    window = _registry(audit)
    w_engine, _, w_workflow = approved_suspension(window, tmp_path / "window", eh._Bindings())
    key = f"{w_workflow.definition.tenant}/{EXECUTION}"
    audit.armed = True
    with pytest.raises(OSError) as raised:
        asyncio.run(resume(w_engine, w_workflow))
    audit.armed = False
    # The failing call's one signal is the audit log's own error, as raised.
    assert len(audit.raised) == 1 and raised.value is audit.raised[0]

    # The control: the same passage committed WITH its row, then interrupted
    # inside the step after the gate, before that step finished.
    control = _registry(AuditLog())
    bindings = BlockingOnceBindings()
    c_engine, _, c_workflow = approved_suspension(control, tmp_path / "control", bindings)

    async def interrupt_inside_the_step() -> None:
        task = asyncio.create_task(resume(c_engine, c_workflow))
        for _ in range(10_000):
            if bindings.blocked:
                break
            await asyncio.sleep(0)
        assert bindings.blocked, "the control's resumption never reached the step after the gate"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(interrupt_inside_the_step())

    # The state record is the same in both: running at the step after the gate.
    # Each names its own store (D-IMPL-391), so the two independent stores'
    # records are compared with the store identity masked (ruling 3(a)).
    record = state_of(window, key)
    controlled = state_of(control, key)
    assert (record.status, record.current_state) == ("running", DOWNSTREAM)
    assert record.state_store_identity == getattr(window.state_store, "identity", None)
    assert controlled.state_store_identity == getattr(control.state_store, "identity", None)
    unnamed = {"state_store_identity": None}
    assert record.model_copy(update=unnamed) == controlled.model_copy(update=unnamed)

    # A later resumption is refused the same way in both.
    later = asyncio.run(resume(w_engine, w_workflow))
    assert isinstance(later, WorkflowResumeRefused), later
    assert INTERRUPTED in later.reason, later.reason
    assert later == asyncio.run(resume(c_engine, c_workflow))

    # The two audit logs differ by exactly the missing row: the control's one
    # attributed passage row, which names the approver.
    w_rows = [comparable(event) for event in events_for(window, key)]
    c_rows = [comparable(event) for event in events_for(control, key)]
    attributed = [row for row in c_rows if row["action"] == "workflow_resumed" and row["resolved"]]
    assert [row["actor"] for row in attributed] == [APPROVER]
    assert [row for row in c_rows if row not in attributed] == w_rows
