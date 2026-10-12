# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The workflow engine refuses queue/store sharing it cannot keep to one passage (Tuesday GO, item 4).

Dave, 2026-10-11 14:51: *"Approval: implement the refusal of unsupported
queue/store sharing; prove a permitted approval still completes exactly once;
state the scope precisely."*

Two compositions were measured to spend ONE approval on TWO passages
(``records/2026-10-09-d-impl-378-designs/designs/beta/DESIGN-2b-store-identity.md``
§2, probes ``p_b09`` and ``p2b_restart`` on ``dl-378-record``):

* one HITL transport shared by two engines whose process-scoped state stores
  are independent (both suspend the same execution id, one approval releases
  both); and
* a transport declaring ``shared`` scope beside a process-scoped store (the
  store is lost at a restart, the transport and its approval are not).

``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine`` now refuses both at
construction. **Scope, precisely:** the refusal covers one Python process. A
process-scoped store may be paired only with a process-scoped transport, and a
process-scoped transport may serve only the one state-store object it was
first built with. Independent *shared* stores reached through one shared queue
in different processes cannot be distinguished by this check; that composition
is excluded by the bank deployment configuration (one workflow engine, state
store and approval queue per instance), not by code. Test vocabulary only
(CINV-01).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ccf.controlplane.state import InMemoryStateStore
from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.workflow.engine import WorkflowEngine, WorkflowSuspended, WorkflowWiringError
from tests.hitl.sec006_harness import execute_as_principal
from tests.workflow import test_engine as eh
from tests.workflow import test_sec006_engine_controls as s6
from tests.workflow.test_engine_refuses_unsupported_seams import SharedStore, SharedTransport, build
from tests.workflow.test_resume_single_flight import (
    APPROVER,
    DOWNSTREAM,
    EXECUTION,
    STARTER,
    engine_over,
    plane,
    resume,
)

#: The refusals' own phrases (``WorkflowEngine.__init__``).
PROCESS_STORE_SHARED_TRANSPORT = "the HITL transport is shared between processes but the Control Plane state store is not"
SECOND_STORE = "is already bound to another Control Plane state store"


def test_a_process_scoped_store_with_a_shared_transport_is_refused(tmp_path: Path) -> None:
    """The restart shape: the store is lost, the shared queue and its approval are not."""
    with pytest.raises(WorkflowWiringError, match=PROCESS_STORE_SHARED_TRANSPORT):
        build(tmp_path, store=InMemoryStateStore(), transport=SharedTransport())


def test_one_process_transport_over_two_independent_stores_is_refused(tmp_path: Path) -> None:
    """The panel shape (``p_b09``): the second engine over a new store object is refused."""
    transport = InMemoryHitlTransport()
    build(tmp_path / "a", store=InMemoryStateStore(), transport=transport)
    with pytest.raises(WorkflowWiringError, match=SECOND_STORE):
        build(tmp_path / "b", store=InMemoryStateStore(), transport=transport)


def test_a_transport_whose_first_store_is_gone_still_refuses_a_new_store(tmp_path: Path) -> None:
    """A restart inside one process: the first store object was dropped, the transport kept."""
    import gc

    transport = InMemoryHitlTransport()
    build(tmp_path / "life-1", store=InMemoryStateStore(), transport=transport)
    gc.collect()
    with pytest.raises(WorkflowWiringError, match=SECOND_STORE):
        build(tmp_path / "life-2", store=InMemoryStateStore(), transport=transport)


def test_rebuilding_an_engine_over_the_same_store_and_transport_is_admitted(tmp_path: Path) -> None:
    """Positive control: the ordinary product path builds engines over one pair repeatedly."""
    store, transport = InMemoryStateStore(), InMemoryHitlTransport()
    assert isinstance(build(tmp_path / "a", store=store, transport=transport), WorkflowEngine)
    assert isinstance(build(tmp_path / "b", store=store, transport=transport), WorkflowEngine)


def test_one_shared_transport_over_two_shared_store_views_is_admitted(tmp_path: Path) -> None:
    """Positive control: replicas over one durable store each hold their own view of it."""
    transport = SharedTransport()
    build(tmp_path / "a", store=SharedStore(), transport=transport)
    assert isinstance(build(tmp_path / "b", store=SharedStore(), transport=transport), WorkflowEngine)


def test_a_permitted_approval_completes_exactly_once(tmp_path: Path) -> None:
    """One approval, two resumptions on the permitted pair: the step after the gate runs once."""
    bindings = eh._Bindings()
    transport = InMemoryHitlTransport()
    registry = plane(InMemoryStateStore())
    workflow = s6._two_gate(registry, eligible=frozenset({STARTER, APPROVER}))
    engine = engine_over(registry, tmp_path, bindings, transport)
    tenant = workflow.definition.tenant
    starter = execute_as_principal(tenant=tenant, resource=workflow.definition_key, principal=STARTER)
    suspended = asyncio.run(engine.execute(starter, workflow, execution_id=EXECUTION))
    assert isinstance(suspended, WorkflowSuspended)
    eh._resolve_gate(
        registry, transport, tenant=tenant, event_key=suspended.event_key, action="approve", subject_id=APPROVER
    )
    first = asyncio.run(resume(engine, workflow))
    second = asyncio.run(resume(engine, workflow))
    assert bindings.ran.count(f"skill:{DOWNSTREAM}") == 1, (first, second, bindings.ran)
    # The first resumption passed the first gate and stopped at the second.
    assert isinstance(first, WorkflowSuspended) and first.event_key != suspended.event_key
