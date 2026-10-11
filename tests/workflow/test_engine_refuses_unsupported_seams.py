"""The workflow engine refuses, at construction, a seam that cannot keep one approval to one passage (D-IMPL-378).

Dave's ruling (2026-10-07): *"Unsupported third-party implementations must fail
at construction."* A gate's passage is exactly-once only over a Control Plane
state store with a conditional write
(:class:`~ccf.controlplane.state.ConditionalStateStore`) and a HITL transport
whose gate closure is atomic with its submissions
(:meth:`~ccf.hitl.transport.HITLTransportProtocol.close_gate`), and only when a
store several processes share is paired with a transport they share too. So
``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine`` refuses each
unsupported shape when it is built — typed, by name — never at the first
resumption. Each test names the refusal by its own phrase; the positive control
shows the reference seams and a shared pair are admitted, so no refusal here
can come from a broken composition. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import InMemoryStateStore
from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.workflow.engine import WorkflowEngine, WorkflowWiringError
from tests.workflow import test_engine as eh
from tests.workflow.test_resume_single_flight import engine_over

#: The refusals' own phrases (``WorkflowEngine.__init__``).
NOT_CONDITIONAL = "is not a ConditionalStateStore declaring a scope"
NOT_THE_WHOLE_TRANSPORT = "does not offer the whole HITLTransportProtocol"
SHARED_STORE_PROCESS_TRANSPORT = "is shared between processes but the HITL transport is not"


class StoreWithoutConditionalWrite:
    """A store that honours :class:`~ccf.controlplane.state.ControlPlaneStateStore`
    as it stood before ``D-IMPL-378`` — ``get``, ``put``, ``items`` — and offers
    no conditional write: the third-party shape the ruling refuses."""

    def __init__(self) -> None:
        self._inner = InMemoryStateStore()

    def get(self, record_class: str, key: str) -> object | None:
        return self._inner.get(record_class, key)

    def put(self, authorized: Any, record_class: str, record: object, *, record_id: str, token: Any) -> None:
        self._inner.put(authorized, record_class, record, record_id=record_id, token=token)

    def items(self, record_class: str) -> tuple[tuple[str, object], ...]:
        return self._inner.items(record_class)


class StoreDeclaringAnUnknownScope(InMemoryStateStore):
    """Every method, and a scope that is neither ``process`` nor ``shared``."""

    scope = "everywhere"


class SharedStore(InMemoryStateStore):
    """Stands in for a durable store several processes reach."""

    scope = "shared"


class SharedTransport(InMemoryHitlTransport):
    """Stands in for a durable transport several processes reach."""

    scope = "shared"


class TransportWithoutClosure:
    """A transport that honours :class:`~ccf.hitl.transport.HITLTransportProtocol`
    as it stood before ``D-IMPL-378`` — and offers no ``close_gate``,
    ``closures`` or ``scope``."""

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


def build(tmp_path: Path, *, store: Any, transport: Any) -> WorkflowEngine:
    registry = ControlPlaneRegistry(clock=eh._ticking_clock(), state_store=store)
    return engine_over(registry, tmp_path, eh._Bindings(), transport)


def test_a_store_without_the_conditional_write_is_refused_at_construction(tmp_path: Path) -> None:
    with pytest.raises(WorkflowWiringError, match=NOT_CONDITIONAL):
        build(tmp_path, store=StoreWithoutConditionalWrite(), transport=InMemoryHitlTransport())


def test_a_store_declaring_an_unknown_scope_is_refused_at_construction(tmp_path: Path) -> None:
    with pytest.raises(WorkflowWiringError, match=NOT_CONDITIONAL):
        build(tmp_path, store=StoreDeclaringAnUnknownScope(), transport=InMemoryHitlTransport())


def test_a_transport_without_the_gate_closure_is_refused_at_construction(tmp_path: Path) -> None:
    with pytest.raises(WorkflowWiringError, match=NOT_THE_WHOLE_TRANSPORT):
        build(tmp_path, store=InMemoryStateStore(), transport=TransportWithoutClosure())


def test_a_shared_store_with_a_process_scoped_transport_is_refused_at_construction(
    tmp_path: Path,
) -> None:
    """A verdict recorded through another process's transport would never be
    judged here, and its gate closures never seen."""
    with pytest.raises(WorkflowWiringError, match=SHARED_STORE_PROCESS_TRANSPORT):
        build(tmp_path, store=SharedStore(), transport=InMemoryHitlTransport())


@pytest.mark.parametrize(
    ("store_type", "transport_type"),
    [
        (InMemoryStateStore, InMemoryHitlTransport),
        (SharedStore, SharedTransport),
        (InMemoryStateStore, SharedTransport),
    ],
    ids=["reference-pair", "shared-pair", "process-store-shared-transport"],
)
def test_the_supported_seams_are_admitted(
    tmp_path: Path, store_type: type[Any], transport_type: type[Any]
) -> None:
    """Positive control: every refusal above is the shape's, not the composition's."""
    assert isinstance(build(tmp_path, store=store_type(), transport=transport_type()), WorkflowEngine)


def test_the_shipped_reference_seams_declare_process_scope() -> None:
    """The SDK's own store and transport reach no other process, and say so."""
    assert InMemoryStateStore().scope == "process"
    assert InMemoryHitlTransport().scope == "process"
