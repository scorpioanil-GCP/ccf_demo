# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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
can come from a broken composition.

Design 1.4 (``D-IMPL-391``) adds two refusals. A state store that declares no
well-formed identity (64 lowercase hex characters) is refused by the identity
rule, by name — decision 2 (b): *"Unsupported implementations refuse
construction"* — never by the generic "not a ConditionalStateStore" message. And
a store or transport declaring ``scope = "process"`` must offer
``writer_lease()``, the single-process lease Dave's ruling 2(a) requires
(*"Stores labeled single-process get the graph store's lock."*); one that does
not is refused by name, before anything is bound.

Dave's ruling of 2026-10-17 18:54 MST (option 3) adds ``retire`` to the
transport Protocol — the queue step that removes a paused run's requests by
their exact fingerprint and leaves no claim (*"Third-party queues must implement
the new exact-fingerprint removal"*) — so a transport without it does not offer
the whole Protocol and is refused at construction. Test vocabulary only
(CINV-01).
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
IDENTITY_RULE = "declares no stable identity"
NO_WRITER_LEASE = "offers no writer_lease"


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


class TransportWithoutRetire:
    """The whole :class:`~ccf.hitl.transport.HITLTransportProtocol` as it stood
    before Dave's ruling of 2026-10-17 18:54 MST — scope, closure, eligibility
    binding and lease included — and no ``retire``."""

    scope = "process"

    def __init__(self) -> None:
        self._inner = InMemoryHitlTransport()

    def __getattr__(self, name: str) -> Any:
        if name == "retire":
            raise AttributeError(name)
        return getattr(self._inner, name)

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


def test_a_transport_without_the_fingerprint_retirement_is_refused_at_construction(
    tmp_path: Path,
) -> None:
    with pytest.raises(WorkflowWiringError, match=NOT_THE_WHOLE_TRANSPORT):
        build(tmp_path, store=InMemoryStateStore(), transport=TransportWithoutRetire())


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
    ],
    ids=["reference-pair", "shared-pair"],
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


# --- design 1.4 (D-IMPL-391) --------------------------------------------------------


class StoreWithoutIdentity(InMemoryStateStore):
    """Every method of the conditional write, and no identity."""

    identity = None  # type: ignore[assignment]


class StoreWithMalformedIdentity(InMemoryStateStore):
    """An identity one hex character short of the declared shape."""

    identity = "a" * 63  # type: ignore[assignment]


class ProcessStoreWithoutLease(InMemoryStateStore):
    """A single-process store that offers no writer lease."""

    writer_lease = None  # type: ignore[assignment]


class ProcessTransportWithoutLease(InMemoryHitlTransport):
    """A single-process transport that offers no writer lease."""

    writer_lease = None  # type: ignore[assignment]


class SharedStoreWithoutLease(SharedStore):
    writer_lease = None  # type: ignore[assignment]


class SharedTransportWithoutLease(SharedTransport):
    writer_lease = None  # type: ignore[assignment]


class _AlwaysEqual(str):
    """A ``str`` whose comparisons always agree: it would make every record look
    like this store's own (found by the independent review of the build)."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = str.__hash__


class StoreWithAStrSubclassIdentity(InMemoryStateStore):
    """The right shape, in a ``str`` subclass that can override comparison."""

    identity = _AlwaysEqual("a" * 64)  # type: ignore[assignment]


@pytest.mark.parametrize(
    "store_type",
    [StoreWithoutIdentity, StoreWithMalformedIdentity, StoreWithAStrSubclassIdentity],
    ids=["missing", "63-hex", "str-subclass"],
)
def test_a_store_without_a_well_formed_identity_is_refused_by_the_identity_rule(
    tmp_path: Path, store_type: type[Any]
) -> None:
    with pytest.raises(WorkflowWiringError, match=IDENTITY_RULE):
        build(tmp_path, store=store_type(), transport=InMemoryHitlTransport())


def test_a_single_process_store_without_a_writer_lease_is_refused_and_binds_nothing(
    tmp_path: Path,
) -> None:
    transport = InMemoryHitlTransport()
    with pytest.raises(WorkflowWiringError, match=NO_WRITER_LEASE):
        build(tmp_path, store=ProcessStoreWithoutLease(), transport=transport)
    assert transport._engine_planes == (), "a refused construction bound its Control Plane"


def test_a_single_process_transport_without_a_writer_lease_is_refused_and_binds_nothing(
    tmp_path: Path,
) -> None:
    transport = ProcessTransportWithoutLease()
    with pytest.raises(WorkflowWiringError, match=NO_WRITER_LEASE):
        build(tmp_path, store=InMemoryStateStore(), transport=transport)
    assert transport._engine_planes == (), "a refused construction bound its Control Plane"


def test_shared_seams_need_no_writer_lease(tmp_path: Path) -> None:
    """Guard: a ``"shared"`` store and transport are multi-process by
    declaration; design 1.4's identity, not a lease, makes them safe."""
    engine = build(tmp_path, store=SharedStoreWithoutLease(), transport=SharedTransportWithoutLease())
    assert isinstance(engine, WorkflowEngine)


def test_the_shipped_reference_seams_offer_the_process_scope_declaration() -> None:
    """The in-memory store and transport return the ``"process"`` declaration:
    exact, because no other process can reach their memory."""
    for seam in (InMemoryStateStore(), InMemoryHitlTransport()):
        offer = getattr(seam, "writer_lease", None)
        assert callable(offer), f"{type(seam).__name__} offers no writer_lease"
        assert offer().scope == "process"
