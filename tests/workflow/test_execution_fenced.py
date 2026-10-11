"""A passage's later writes are fenced by the version its commit wrote (D-IMPL-378).

Since ``D-IMPL-378`` a resumption commits its passage — the record ``running``
past the gate — before the step after the gate runs, and the write that ends
the passage (suspension, exception or completion) is conditional on the version
that commit wrote
(``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._fenced_write``).
The engine's own refusals keep every other engine off a ``running`` execution,
so on a conforming store only a writer outside the engine can move it. This
module plays that writer: while the step after the gate runs, another
:class:`~ccf.controlplane.state.AuditedStateWriter` over the same store writes
the execution's record. The passage's next write then raises
:class:`~ccf_runtime.workflow.engine.ExecutionFenced`, and writes, appends and
enqueues nothing, so the other writer's record stands. The positive control is
the same passage with no other writer, which suspends at the next gate. Test
vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ccf.controlplane.audit import AuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import AuditedStateWriter, InMemoryStateStore
from ccf_runtime.workflow.engine import ExecutionFenced, WorkflowSuspended
from ccf_runtime.workflow.state import WORKFLOW_STATE
from tests.workflow import test_engine as eh
from tests.workflow.test_resume_single_flight import (
    DOWNSTREAM,
    EXECUTION,
    NEXT_GATE,
    approved_suspension,
    plane,
    resume,
)


class OtherWriterBindings(eh._Bindings):
    """While the step after the gate runs, ``move`` runs once — the writer
    outside the engine."""

    def __init__(self) -> None:
        super().__init__()
        self.move: Callable[[], None] | None = None

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        if step_name == DOWNSTREAM and self.move is not None:
            move, self.move = self.move, None
            move()
        return await super().run_skill(tenant=tenant, step_name=step_name, ref=ref)


def suspensions_audited(registry: ControlPlaneRegistry, key: str) -> list[AuditEvent]:
    return [
        event
        for event in registry.audit_log.events()
        if event.key == key and event.action == "workflow_suspended"
    ]


def test_a_record_moved_by_another_writer_while_the_step_runs_fences_the_passage(
    tmp_path: Path,
) -> None:
    store = InMemoryStateStore()
    registry = plane(store)
    bindings = OtherWriterBindings()
    engine, transport, workflow = approved_suspension(registry, tmp_path, bindings)
    tenant = workflow.definition.tenant
    key = f"{tenant}/{EXECUTION}"
    before = suspensions_audited(registry, key)
    moved: list[tuple[object | None, int]] = []

    def move() -> None:
        record, version = store.get_versioned(WORKFLOW_STATE, key)
        assert getattr(record, "status", None) == "running", record
        AuditedStateWriter(store=store, audit=registry.audit_log).write(
            eh.execute_as(workflow),
            WORKFLOW_STATE,
            record,
            record_id=EXECUTION,
            event=AuditEvent(
                sequence=0,
                action="state_written",
                key=key,
                version=workflow.identity.definition_hash,
                resolved=True,
                occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
            ),
        )
        moved.append(store.get_versioned(WORKFLOW_STATE, key))
        assert moved[0][1] == version + 1

    bindings.move = move
    with pytest.raises(ExecutionFenced, match="was moved by another writer"):
        asyncio.run(resume(engine, workflow))

    assert moved, "the other writer never ran"
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 1
    # Nothing was written over the other writer's record, no suspension was
    # audited, and the next gate is not offered.
    assert store.get_versioned(WORKFLOW_STATE, key) == moved[0]
    assert suspensions_audited(registry, key) == before
    assert not [
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == f"{key}/{NEXT_GATE}"
    ]


def test_the_same_passage_with_no_other_writer_suspends_at_the_next_gate(tmp_path: Path) -> None:
    """Positive control: no writer outside the engine, so the fence never
    fires and the passage ends at the next gate."""
    registry = plane()
    engine, transport, workflow = approved_suspension(registry, tmp_path, OtherWriterBindings())
    tenant = workflow.definition.tenant
    key = f"{tenant}/{EXECUTION}"
    before = suspensions_audited(registry, key)
    outcome = asyncio.run(resume(engine, workflow))
    assert isinstance(outcome, WorkflowSuspended), outcome
    assert outcome.gate == NEXT_GATE
    # The two things the fenced passage must not do, done here: a suspension
    # audited and the next gate offered.
    assert len(suspensions_audited(registry, key)) == len(before) + 1
    assert [
        event
        for event in transport.pending(tenant=tenant)
        if event.event_key == f"{key}/{NEXT_GATE}"
    ]
