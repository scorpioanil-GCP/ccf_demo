"""Conformance for the two atomic acts one approval's single passage stands on (D-IMPL-378).

Dave's ruling (2026-10-07) approved the atomic gate close and the conditional
state write, with unsupported implementations refused at construction. The
workflow engine refuses a seam that lacks the methods
(``tests/workflow/test_engine_refuses_unsupported_seams.py``), but it cannot see
whether an implementation keeps the atomicity it declares. This suite is that
acceptance bar, run against the SDK's reference implementations here; a
deployment adds its own durable implementation's factory to :data:`TRANSPORTS`
or :data:`STORES` and runs it unchanged:

* :meth:`~ccf.hitl.transport.HITLTransportProtocol.close_gate` — racing
  closures of one passage return one closure; racing passages admit exactly
  one; a verdict racing the closure is either inside the population the
  closure judged or refused by name, never both; a closure retires only its own
  suspension's event; a stale count changes nothing.
* :meth:`~ccf.controlplane.state.ConditionalStateStore.put_if` — racing
  creates admit one; racing writes from one version admit one; an
  unconditional write moves the version a conditional writer reads; a refused
  write writes nothing and appends no audit event.

Every race starts its threads at one barrier. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.state import AuditedStateWriter, InMemoryStateStore, StateConflict, state_key
from ccf.hitl.transport import (
    GateAlreadyClosed,
    GateClosure,
    GateVerdictsChanged,
    HitlActionSubmission,
    HitlGateClosed,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from tests.hitl.capabilities import submit_capability
from tests.workflow import test_engine as eh
from tests.workflow.capabilities import execute_capability, resume_capability

#: Every factory a deployment's own implementation joins.
TRANSPORTS = [pytest.param(InMemoryHitlTransport, id="in-memory-transport")]
STORES = [pytest.param(InMemoryStateStore, id="in-memory-store")]

THREADS = 16
TENANT = "conformance-tenant"
WORKFLOW_KEY = "conformance/workflows/gate"
EXECUTION = f"{TENANT}/exec"
EVENT_KEY = f"{EXECUTION}/gate"
SUSPENSION = "a" * 64
LATER_SUSPENSION = "b" * 64
RECORD_CLASS = "conformance.state"
INSTANT = datetime(2026, 10, 7, tzinfo=UTC)


def race(count: int, call: Callable[[int], Any]) -> list[tuple[str, Any]]:
    """``call(i)`` on ``count`` threads released by one barrier; each outcome
    is ``("ok", value)`` or ``("raised", exception)``."""
    barrier = threading.Barrier(count)
    outcomes: list[tuple[str, Any]] = [("none", None)] * count

    def run(index: int) -> None:
        barrier.wait()
        try:
            outcomes[index] = ("ok", call(index))
        except BaseException as error:  # every outcome is asserted on below
            outcomes[index] = ("raised", error)

    threads = [threading.Thread(target=run, args=(i,), daemon=True) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
        assert not thread.is_alive(), "a racing thread never finished"
    return outcomes


def gate_event(suspension: str = SUSPENSION) -> PendingHitlEvent:
    return PendingHitlEvent(
        event_key=EVENT_KEY,
        event_class="approval-gate",
        tenant=TENANT,
        workflow_state_ref=EXECUTION,
        product_content_hash=suspension,
    )


def close(transport: Any, *, passage: str, observed: int, suspension: str = SUSPENSION) -> GateClosure:
    closure: GateClosure = transport.close_gate(
        resume_capability(tenant=TENANT, resource=WORKFLOW_KEY),
        event_key=EVENT_KEY,
        product_content_hash=suspension,
        passage=passage,
        decided_action="approve",
        decided_by="officer-1",
        observed_submissions=observed,
    )
    return closure


def submit(transport: Any, *, subject: str, action: str = "reject", suspension: str = SUSPENSION) -> Any:
    return transport.submit(
        submit_capability(tenant=TENANT, principal=subject, event_key=EVENT_KEY),
        submission=HitlActionSubmission(
            event_key=EVENT_KEY,
            action=action,
            principal=eh._binding(suspension, subject_id=subject, verdict=action),
        ),
    )


def on_suspension(transport: Any, suspension: str = SUSPENSION) -> list[Any]:
    return [
        s
        for s in transport.submissions(tenant=TENANT)
        if s.event_key == EVENT_KEY and s.principal.product_content_hash == suspension
    ]


# --- the gate's closure ---------------------------------------------------------------


@pytest.mark.parametrize("make", TRANSPORTS)
def test_racing_closures_of_one_passage_return_one_closure(make: Callable[[], Any]) -> None:
    transport = make()
    transport.enqueue(event=gate_event())
    outcomes = race(THREADS, lambda _: close(transport, passage="the-passage", observed=0))
    assert [kind for kind, _ in outcomes] == ["ok"] * THREADS, outcomes
    closures = {value for _, value in outcomes}
    assert len(closures) == 1, closures
    assert transport.closures(tenant=TENANT) == tuple(closures)


@pytest.mark.parametrize("make", TRANSPORTS)
def test_racing_closures_by_different_passages_admit_exactly_one(make: Callable[[], Any]) -> None:
    transport = make()
    transport.enqueue(event=gate_event())
    outcomes = race(THREADS, lambda i: close(transport, passage=f"passage-{i}", observed=0))
    won = [value for kind, value in outcomes if kind == "ok"]
    lost = [value for kind, value in outcomes if kind == "raised"]
    assert len(won) == 1, outcomes
    assert len(lost) == THREADS - 1 and all(isinstance(e, GateAlreadyClosed) for e in lost), lost
    assert transport.closures(tenant=TENANT) == (won[0],)


@pytest.mark.parametrize("make", TRANSPORTS)
def test_a_verdict_racing_the_closure_is_judged_or_refused_never_both(make: Callable[[], Any]) -> None:
    """The property limit (b) needed: when the closure lands, every verdict
    recorded on the suspension is inside the count it judged, and every verdict
    after it is refused by name."""
    transport = make()
    transport.enqueue(event=gate_event())
    submitters = THREADS - 1

    def act(index: int) -> Any:
        if index == submitters:  # the closer: judge, and judge again if a verdict landed meanwhile
            for _ in range(1_000):
                try:
                    return close(transport, passage="the-passage", observed=len(on_suspension(transport)))
                except GateVerdictsChanged:
                    continue
            raise AssertionError("the closer never judged a stable population")
        return submit(transport, subject=f"officer-{index}")

    outcomes = race(THREADS, act)
    kind, closure = outcomes[submitters]
    assert kind == "ok" and isinstance(closure, GateClosure), outcomes[submitters]
    recorded = on_suspension(transport)
    assert closure.observed_submissions == len(recorded), (closure, recorded)
    admitted = [value for kind, value in outcomes[:submitters] if kind == "ok"]
    refused = [value for kind, value in outcomes[:submitters] if kind == "raised"]
    assert all(isinstance(e, HitlGateClosed) for e in refused), refused
    assert len(admitted) == len(recorded) and len(admitted) + len(refused) == submitters
    with pytest.raises(HitlGateClosed):
        submit(transport, subject="officer-after-the-race")


@pytest.mark.parametrize("make", TRANSPORTS)
def test_a_closure_retires_its_own_suspension_only(make: Callable[[], Any]) -> None:
    """A later suspension of the same gate (a loop) shares the event key and
    keeps its event and its verdicts."""
    transport = make()
    transport.enqueue(event=gate_event(SUSPENSION))
    transport.enqueue(event=gate_event(LATER_SUSPENSION))
    close(transport, passage="the-passage", observed=0)
    pending = [e.product_content_hash for e in transport.pending(tenant=TENANT) if e.event_key == EVENT_KEY]
    assert pending == [LATER_SUSPENSION], pending
    with pytest.raises(HitlGateClosed):
        submit(transport, subject="officer-2", suspension=SUSPENSION)
    recorded = submit(transport, subject="officer-2", suspension=LATER_SUSPENSION)
    assert recorded.event_state_at_submit == "pending"
    assert on_suspension(transport, SUSPENSION) == []


@pytest.mark.parametrize("make", TRANSPORTS)
def test_a_stale_count_changes_nothing(make: Callable[[], Any]) -> None:
    transport = make()
    transport.enqueue(event=gate_event())
    submit(transport, subject="officer-2")
    with pytest.raises(GateVerdictsChanged):
        close(transport, passage="the-passage", observed=0)
    assert transport.closures(tenant=TENANT) == ()
    assert [e.event_key for e in transport.pending(tenant=TENANT)] == [EVENT_KEY]
    assert submit(transport, subject="officer-3").event_state_at_submit == "pending"
    closure = close(transport, passage="the-passage", observed=2)
    assert closure.observed_submissions == 2


# --- the conditional state write -------------------------------------------------------


def writer(make: Callable[[], Any]) -> tuple[Any, AuditedStateWriter, AuditLog]:
    store = make()
    audit = AuditLog()
    return store, AuditedStateWriter(store=store, audit=audit), audit


def write_if(writer_: AuditedStateWriter, record: object, *, expected: int) -> int:
    _, version = writer_.write_if(
        execute_capability(tenant=TENANT, resource=WORKFLOW_KEY),
        RECORD_CLASS,
        record,
        record_id="the-record",
        event=AuditEvent(
            sequence=0,
            action="state_written",
            key=state_key(tenant=TENANT, record_id="the-record"),
            version="1",
            resolved=True,
            occurred_at=INSTANT,
        ),
        expected_version=expected,
    )
    return version


KEY = state_key(tenant=TENANT, record_id="the-record")


@pytest.mark.parametrize("make", STORES)
def test_racing_creates_admit_exactly_one(make: Callable[[], Any]) -> None:
    store, writer_, audit = writer(make)
    outcomes = race(THREADS, lambda i: write_if(writer_, {"writer": i}, expected=0))
    won = [i for i, (kind, _) in enumerate(outcomes) if kind == "ok"]
    lost = [value for kind, value in outcomes if kind == "raised"]
    assert len(won) == 1, outcomes
    assert all(isinstance(e, StateConflict) for e in lost), lost
    assert store.get_versioned(RECORD_CLASS, KEY) == ({"writer": won[0]}, 1)
    assert len(audit.events()) == 1


@pytest.mark.parametrize("make", STORES)
def test_racing_writes_from_one_version_admit_exactly_one(make: Callable[[], Any]) -> None:
    store, writer_, audit = writer(make)
    assert write_if(writer_, {"writer": "first"}, expected=0) == 1
    outcomes = race(THREADS, lambda i: write_if(writer_, {"writer": i}, expected=1))
    won = [i for i, (kind, _) in enumerate(outcomes) if kind == "ok"]
    assert len(won) == 1, outcomes
    assert all(isinstance(v, StateConflict) for kind, v in outcomes if kind == "raised")
    assert store.get_versioned(RECORD_CLASS, KEY) == ({"writer": won[0]}, 2)
    assert len(audit.events()) == 2


@pytest.mark.parametrize("make", STORES)
def test_an_unconditional_write_moves_the_version_a_conditional_writer_reads(
    make: Callable[[], Any],
) -> None:
    store, writer_, _ = writer(make)
    write_if(writer_, {"writer": "first"}, expected=0)
    writer_.write(
        execute_capability(tenant=TENANT, resource=WORKFLOW_KEY),
        RECORD_CLASS,
        {"writer": "unconditional"},
        record_id="the-record",
        event=AuditEvent(
            sequence=0, action="state_written", key=KEY, version="1", resolved=True, occurred_at=INSTANT
        ),
    )
    assert store.get_versioned(RECORD_CLASS, KEY) == ({"writer": "unconditional"}, 2)
    with pytest.raises(StateConflict):
        write_if(writer_, {"writer": "stale"}, expected=1)


@pytest.mark.parametrize("make", STORES)
def test_a_refused_conditional_write_writes_nothing_and_appends_nothing(make: Callable[[], Any]) -> None:
    store, writer_, audit = writer(make)
    write_if(writer_, {"writer": "first"}, expected=0)
    before = (store.get_versioned(RECORD_CLASS, KEY), len(audit.events()))
    with pytest.raises(StateConflict):
        write_if(writer_, {"writer": "stale"}, expected=0)
    assert (store.get_versioned(RECORD_CLASS, KEY), len(audit.events())) == before
