# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The passage commit is two writes, and what the window between them leaves (decision 7 of ``D-IMPL-378``).

Dave, 2026-10-09 06:06 MST, confirmed at 06:21: *"(b), with the documentation
correction now. Make a committed transition without its audit row detectable
and recoverable. Do not claim atomicity that does not exist."*

A resumption commits its passage through
``src/ccf/controlplane/state.py::AuditedStateWriter.write_if``
(``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._write_state``): the
state store's conditional write that moves the execution past its gate, THEN
the audit log's append of the attributed ``workflow_resumed`` row. The final
panel's G-ONEWRITE measured that the documentation called these one write.

Each ``test_limit_*`` below asserts, as it stands, what an operator finds when
the append fails after the state write landed. None is a fix: making such a
transition detectable and recoverable (7 (b)) is being designed, not built.
When that design changes the behavior these tests go red, and
``public/how-to/security-and-deployment.md`` §4.13, which states them, must
change with them. The last test holds the published pages to the correction.

The failure sits in the second write and nowhere else: an
:class:`~ccf.controlplane.audit.AuditLog` whose append of ``workflow_resumed``
fails once armed, injected through the Control Plane registry the engine reads
its audit log from. Composition reuses
``tests/workflow/test_resume_single_flight.py`` and
``tests/workflow/test_approval_gate_limits.py``. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowResumeRefused,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE
from tests.workflow import test_engine as eh
from tests.workflow.test_approval_gate_limits import (
    APPROVING_TERMINAL,
    COVENANT_EXECUTION,
    FIRST_GATE,
    OFFICER_1,
    attributed_resumptions,
    resume_covenant,
    state_of,
)
from tests.workflow.test_resume_single_flight import (
    APPROVER,
    DOWNSTREAM,
    EXECUTION,
    INTERRUPTED,
    approved_suspension,
    resume,
)

REPO = Path(__file__).resolve().parents[2]
PAGE = "public/how-to/security-and-deployment.md"
REGISTER = "public/reference/controls-register.md"
#: The code the page must name for the two writes, and the tests that measure
#: the window it must point a reader to.
WRITE_IF = "src/ccf/controlplane/state.py::AuditedStateWriter.write_if"
MEASURED_BY = (
    "tests/controlplane/test_audited_write_is_two_writes.py",
    "tests/workflow/test_passage_commit_two_writes_limits.py",
)

#: What the stand-in audit log raises, so each assertion names its own failure.
UNAVAILABLE = "audit log unavailable between the two writes"


class _ResumedRowFails(AuditLog):
    """An audit log whose append of ``workflow_resumed`` fails while armed."""

    armed = False

    def append(self, **kwargs: Any) -> AuditEvent:
        if self.armed and kwargs.get("action") == "workflow_resumed":
            raise OSError(UNAVAILABLE)
        return super().append(**kwargs)


def _registry(audit: AuditLog) -> ControlPlaneRegistry:
    """``tests/workflow/test_resume_single_flight.py::plane``'s body, over ``audit``."""
    registry = ControlPlaneRegistry(clock=eh._ticking_clock(), audit_log=audit)
    eh._register_covenant_closure(registry)
    eh._register_refresh_closure(registry)
    return registry


def _decided(transport: InMemoryHitlTransport, *, tenant: str, event_key: str) -> list[tuple[str, str]]:
    """The gate's closure on the authority path: the verdict and who decided it."""
    return [
        (closure.decided_action, closure.decided_by)
        for closure in transport.closures(tenant=tenant)
        if closure.event_key == event_key
    ]


def _version(registry: ControlPlaneRegistry, key: str) -> int:
    store = registry.state_store
    assert hasattr(store, "get_versioned")
    _, version = store.get_versioned(WORKFLOW_STATE, key)
    assert isinstance(version, int)
    return version


def test_limit_a_failed_row_append_leaves_the_execution_past_its_gate_with_no_resumed_row(
    tmp_path: Path,
) -> None:
    """The decision leads to a step. The passage commit landed and its row did not."""
    audit = _ResumedRowFails()
    registry = _registry(audit)
    bindings = eh._Bindings()
    engine, transport, workflow = approved_suspension(registry, tmp_path, bindings)
    tenant = workflow.definition.tenant
    key = f"{tenant}/{EXECUTION}"
    gate = f"{key}/{FIRST_GATE}"
    record = state_of(registry, key)
    assert (record.status, record.current_state) == ("suspended", FIRST_GATE)
    before = _version(registry, key)

    audit.armed = True
    with pytest.raises(OSError, match=UNAVAILABLE):
        asyncio.run(resume(engine, workflow))
    audit.armed = False

    # The first write landed: the execution left its gate, one version on.
    record = state_of(registry, key)
    assert (record.status, record.current_state) == ("running", DOWNSTREAM)
    assert _version(registry, key) == before + 1
    # The second did not: no row in the audit log names who approved the passage.
    assert attributed_resumptions((registry,), key) == []
    # The authority path still does, and no longer offers the gate.
    assert _decided(transport, tenant=tenant, event_key=gate) == [("approve", APPROVER)]
    assert [event for event in transport.pending(tenant=tenant) if event.event_key == gate] == []
    # Nothing after the gate ran.
    assert f"skill:{DOWNSTREAM}" not in bindings.ran

    # At a step, every later resumption is refused as an interrupted passage,
    # and the row is never written.
    refused = asyncio.run(resume(engine, workflow))
    assert isinstance(refused, WorkflowResumeRefused)
    assert INTERRUPTED in refused.reason
    assert attributed_resumptions((registry,), key) == []
    assert f"skill:{DOWNSTREAM}" not in bindings.ran


def test_limit_a_terminal_reached_through_the_window_completes_later_with_no_resumed_row(
    tmp_path: Path,
) -> None:
    """The decision leads to a terminal state. A later resumption finishes the
    execution under its closure (Dave's D2), and the completed record still has
    no row naming who approved the passage."""
    audit = _ResumedRowFails()
    registry = _registry(audit)
    engine, transport, workflow, event_key, bound = eh._suspended_covenant(
        registry, tmp_path, execution_id=COVENANT_EXECUTION
    )
    tenant = workflow.definition.tenant
    eh._submit_only(
        transport,
        tenant=tenant,
        event_key=event_key,
        product_content_hash=bound,
        action="approve",
        subject_id=OFFICER_1,
    )
    key = f"{tenant}/{COVENANT_EXECUTION}"

    audit.armed = True
    with pytest.raises(OSError, match=UNAVAILABLE):
        resume_covenant(engine, workflow)
    audit.armed = False

    record = state_of(registry, key)
    assert (record.status, record.current_state) == ("running", APPROVING_TERMINAL)
    assert attributed_resumptions((registry,), key) == []
    assert _decided(transport, tenant=tenant, event_key=event_key) == [("approve", OFFICER_1)]

    completed = resume_covenant(engine, workflow)
    assert isinstance(completed, WorkflowCompleted)
    assert state_of(registry, key).status == "terminal"
    assert attributed_resumptions((registry,), key) == []


def test_the_published_pages_no_longer_claim_the_passage_and_its_row_are_one_write() -> None:
    """The documentation correction Dave ordered "now", held to what was measured.

    Read the way ``tests/erasure/test_sec009_fix5_rulings.py`` reads §4.10:
    exactly §4.13, up to the next heading, and exactly the bullet that states
    the passage commit. That bullet names the code that makes the two writes and
    the tests above, and no longer calls them one write; the controls register's
    row for the same code, and the engine's own docstring, do not either.
    """
    raw = (REPO / PAGE).read_text(encoding="utf-8")
    assert raw.count("\n### 4.13 ") == 1, "SP §4.13's heading moved"
    section = re.split(r"\n#{2,3} ", raw.split("\n### 4.13 ", 1)[1], maxsplit=1)[0]
    bullets = [" ".join(item.split()) for item in re.split(r"\n- ", section)]
    commit = [item for item in bullets if item.startswith("**The conditional passage commit**")]
    assert len(commit) == 1, "the conditional passage commit's bullet is missing from §4.13"

    problems = []
    if "one write" in commit[0]:
        problems.append(f"{PAGE} §4.13 still calls the passage and its row one write")
    for needed in (WRITE_IF, *MEASURED_BY):
        if needed not in commit[0]:
            problems.append(f"{PAGE} §4.13's passage-commit bullet does not name {needed}")
    rows = [
        line
        for line in (REPO / REGISTER).read_text(encoding="utf-8").splitlines()
        if f"`{WRITE_IF}`" in line
    ]
    if not rows:
        problems.append(f"{REGISTER} has no row for {WRITE_IF}")
    problems.extend(
        f"{REGISTER} still names the row for write_if 'one write': {row.split('|')[1].strip()}"
        for row in rows
        if "one write" in row
    )
    docstring = " ".join((WorkflowEngine.resume.__doc__ or "").split()).lower()
    if "one audited write" in docstring:
        problems.append("WorkflowEngine.resume's docstring still says ONE audited write")
    assert not problems, "\n".join(problems)
