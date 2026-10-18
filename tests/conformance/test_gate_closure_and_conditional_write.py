# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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
* :meth:`~ccf.hitl.transport.HITLTransportProtocol.enqueue` (``D-IMPL-391``;
  Dave, 2026-10-17 15:25 MST: *"Third-party transports must meet the
  contract."*) — racing enqueues of one paused run's request file one; a
  request for another pause under the same key is filed.
* :meth:`~ccf.hitl.transport.HITLTransportProtocol.retire` and the judgment of
  :meth:`~ccf.hitl.transport.HITLTransportProtocol.submit` (``D-IMPL-391``;
  Dave, 2026-10-17 18:54 MST: *"Third-party queues must implement the new
  exact-fingerprint removal"*; *"Count an approval sent straight to the queue
  only while the request for this exact pause is waiting."*) — a retirement
  takes every request of one pause wherever it sits, keeps the rest in order and
  records no claim; it discards a claim only on its own pause; racing
  retirements return one request once; a claim on one pause's request is
  neither used nor consumed by a verdict naming another; a verdict naming a
  pause with no request waiting for it is recorded ``missing``, whatever else
  waits under the key.
* :attr:`~ccf.controlplane.state.ConditionalStateStore.identity`
  (``D-IMPL-391``, design 1.4) — 64 lowercase hex characters; one identity for
  every client of one substrate; different for an independent substrate; kept
  by a durable substrate across a reopen; and a copied durable substrate
  refuses to open. The engine checks only the shape; these cases are the bar
  for uniqueness and persistence. :data:`SUBSTRATES` holds the in-memory
  reference, a stand-in for a durable store several processes share, and a
  path-backed single-process stand-in
  (``tests/support/path_backed_approval_pair.py``); a deployment adds its own.

Every race starts its threads at one barrier. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import re
import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
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


# --- one paused run, one request (D-IMPL-391, ruling 4(a)) ---------------------------


@pytest.mark.parametrize("make", TRANSPORTS)
def test_racing_enqueues_of_one_paused_runs_request_file_one(make: Callable[[], Any]) -> None:
    """A race at one barrier: it can only catch a non-atomic enqueue BY CHANCE.
    Measured: with the reference transport's absence check moved outside its
    lock (severing S8), this case passed 5 of 5 runs. The deterministic check is
    the forced interleaving of
    ``tests/hitl/test_enqueue_files_a_paused_runs_request_once.py``, which a
    deployment reproduces against its own transport's check and append."""
    transport = make()
    outcomes = race(THREADS, lambda i: transport.enqueue(event=gate_event()))
    assert all(kind == "ok" for kind, _ in outcomes), outcomes
    queued = [e for e in transport.pending(tenant=TENANT) if e.event_key == EVENT_KEY]
    assert queued == [gate_event()], f"{len(queued)} requests queued for one paused run"


@pytest.mark.parametrize("make", TRANSPORTS)
def test_a_request_for_another_pause_under_the_same_key_is_filed(make: Callable[[], Any]) -> None:
    transport = make()
    transport.enqueue(event=gate_event(SUSPENSION))
    transport.enqueue(event=gate_event(LATER_SUSPENSION))
    assert [e.product_content_hash for e in transport.pending(tenant=TENANT)] == [
        SUSPENSION,
        LATER_SUSPENSION,
    ]


# --- retirement and judgment by the paused run's fingerprint (D-IMPL-391, option 3) ---

OLD_SUSPENSION = "c" * 64


def retire(transport: Any, suspension: str) -> Any:
    method = getattr(transport, "retire", None)
    assert callable(method), f"{type(transport).__name__} offers no retire"
    return method(tenant=TENANT, event_key=EVENT_KEY, product_content_hash=suspension)


def straight_verdict(transport: Any, suspension: str) -> HitlActionSubmission:
    """A verdict naming ``suspension``, sent straight to the queue."""
    recorded: HitlActionSubmission = transport.submit(
        submit_capability(tenant=TENANT, principal="approver", event_key=EVENT_KEY),
        submission=HitlActionSubmission(
            event_key=EVENT_KEY,
            action="approve",
            principal=eh._binding(suspension, subject_id="approver"),
        ),
    )
    return recorded


@pytest.mark.parametrize("make", TRANSPORTS)
def test_a_retirement_takes_one_pause_wherever_it_sits_and_records_no_claim(
    make: Callable[[], Any],
) -> None:
    transport = make()
    for suspension in (SUSPENSION, OLD_SUSPENSION, LATER_SUSPENSION, OLD_SUSPENSION):
        transport.enqueue(event=gate_event(suspension))
    retired = retire(transport, OLD_SUSPENSION)
    assert [e.product_content_hash for e in retired] == [OLD_SUSPENSION]
    assert [e.product_content_hash for e in transport.pending(tenant=TENANT)] == [
        SUSPENSION,
        LATER_SUSPENSION,
    ]
    assert straight_verdict(transport, OLD_SUSPENSION).event_state_at_submit == "missing"


@pytest.mark.parametrize("make", TRANSPORTS)
def test_a_retirement_discards_a_claim_on_its_own_pause_only(make: Callable[[], Any]) -> None:
    own = make()
    own.enqueue(event=gate_event(OLD_SUSPENSION))
    assert own.remove(tenant=TENANT, event_key=EVENT_KEY) is not None
    retire(own, OLD_SUSPENSION)
    assert straight_verdict(own, OLD_SUSPENSION).event_state_at_submit == "missing"

    other = make()
    other.enqueue(event=gate_event(SUSPENSION))
    assert other.remove(tenant=TENANT, event_key=EVENT_KEY) is not None
    retire(other, OLD_SUSPENSION)
    assert straight_verdict(other, SUSPENSION).event_state_at_submit == "claimed"


@pytest.mark.parametrize("make", TRANSPORTS)
def test_a_claim_on_another_pause_neither_stamps_a_verdict_nor_is_consumed_by_it(
    make: Callable[[], Any],
) -> None:
    """The claim half of the per-pause judgment (found missing from this suite by
    the review of ``4be75f02``): a primitive's claim on one pause's request is
    neither used by a verdict naming another pause nor consumed by it, so the
    primitive's own verdict still finds it."""
    transport = make()
    transport.enqueue(event=gate_event(OLD_SUSPENSION))
    transport.enqueue(event=gate_event(SUSPENSION))
    claimed = transport.remove(tenant=TENANT, event_key=EVENT_KEY)
    assert claimed is not None and claimed.product_content_hash == OLD_SUSPENSION
    assert straight_verdict(transport, SUSPENSION).event_state_at_submit == "pending"
    assert straight_verdict(transport, OLD_SUSPENSION).event_state_at_submit == "claimed"


@pytest.mark.parametrize("make", TRANSPORTS)
def test_racing_retirements_of_one_pause_return_its_request_once(make: Callable[[], Any]) -> None:
    """A race at one barrier: like the enqueue race, it can only catch a
    non-atomic retirement BY CHANCE."""
    transport = make()
    transport.enqueue(event=gate_event(OLD_SUSPENSION))
    outcomes = race(THREADS, lambda i: tuple(retire(transport, OLD_SUSPENSION)))
    assert all(kind == "ok" for kind, _ in outcomes), outcomes
    assert sum(len(value) for _, value in outcomes) == 1, outcomes


@pytest.mark.parametrize("make", TRANSPORTS)
def test_a_verdict_naming_a_pause_with_no_request_waiting_is_missing(make: Callable[[], Any]) -> None:
    transport = make()
    transport.enqueue(event=gate_event(OLD_SUSPENSION))
    assert straight_verdict(transport, SUSPENSION).event_state_at_submit == "missing"
    transport.enqueue(event=gate_event(SUSPENSION))
    assert straight_verdict(transport, SUSPENSION).event_state_at_submit == "pending"


# --- the state store's identity (D-IMPL-391, design 1.4) -----------------------------

#: The declared shape (``src/ccf/controlplane/state.py::STATE_STORE_IDENTITY_PATTERN``),
#: restated so this suite reads as the bar, not as a copy of the code it judges.
IDENTITY_SHAPE = re.compile(r"[0-9a-f]{64}")


def identity_of(store: Any) -> str:
    identity = getattr(store, "identity", None)
    assert isinstance(identity, str) and IDENTITY_SHAPE.fullmatch(identity), (
        f"{type(store).__name__} declares no identity of the declared shape: {identity!r}"
    )
    return identity


@dataclass(frozen=True)
class Substrate:
    """How a deployment opens its own store, for the identity cases.

    ``open(location)`` opens a client of the substrate at ``location``, a
    directory a durable store may use. ``second_client(store)`` is another
    client of the same substrate while ``store`` is open. ``reopen(store)``
    closes ``store`` and opens its substrate again; ``None`` for a store whose
    records do not survive a restart. ``copy(store, location)`` copies the
    closed substrate to ``location`` and opens the copy; ``None`` for a store
    with nothing to copy.
    """

    open: Callable[[Path], Any]
    second_client: Callable[[Any], Any]
    reopen: Callable[[Any], Any] | None
    copy: Callable[[Any, Path], Any] | None
    #: What the store raises when opened as a copy; ``None`` with ``copy``.
    copy_refusal: type[BaseException] | None = None
    #: Why ``copy`` is ``None``: the case is SKIPPED with this reason, never passed.
    not_copyable: str = ""


def _in_memory() -> Substrate:
    # An in-memory store's records live in the object, so the object is the
    # substrate: its only client is itself, and a new object is a new store.
    return Substrate(
        open=lambda _: InMemoryStateStore(),
        second_client=lambda s: s,
        reopen=None,
        copy=None,
        not_copyable="its records live in the object; nothing outlives it to copy",
    )


def _shared_backing() -> Substrate:
    from tests.workflow.test_approval_gate_limits import SharedBackingStore, StandInRecords

    return Substrate(
        open=lambda _: SharedBackingStore(StandInRecords()),
        second_client=lambda s: SharedBackingStore(s._records),
        reopen=lambda s: SharedBackingStore(s._records),
        copy=None,
        not_copyable=(
            "the stand-in's shared records are one in-process object; a copy of a"
            " real shared store is that store's own case"
        ),
    )


def _path_backed() -> Substrate:
    from tests.support.path_backed_approval_pair import PathBackedStateStore, SubstrateMoved

    def reopen(store: Any) -> Any:
        store.close()
        return PathBackedStateStore(store.directory)

    def copy(store: Any, location: Path) -> Any:
        store.close()
        shutil.copytree(store.directory, location / "copied")
        return PathBackedStateStore(location / "copied")

    return Substrate(
        open=lambda location: PathBackedStateStore(location / "state"),
        # A single-process store has one client per process: the open one.
        second_client=lambda s: s,
        reopen=reopen,
        copy=copy,
        copy_refusal=SubstrateMoved,
    )


#: Every substrate a deployment's own store joins.
SUBSTRATES = [
    pytest.param(_in_memory, id="in-memory-store"),
    pytest.param(_shared_backing, id="shared-backing-stand-in"),
    pytest.param(_path_backed, id="path-backed-single-process-stand-in"),
]


@pytest.mark.parametrize("substrate", SUBSTRATES)
def test_the_identity_has_the_declared_shape(substrate: Callable[[], Substrate], tmp_path: Path) -> None:
    identity_of(substrate().open(tmp_path))


@pytest.mark.parametrize("substrate", SUBSTRATES)
def test_every_client_of_one_substrate_returns_one_identity(
    substrate: Callable[[], Substrate], tmp_path: Path
) -> None:
    kind = substrate()
    store = kind.open(tmp_path)
    assert identity_of(kind.second_client(store)) == identity_of(store)


@pytest.mark.parametrize("substrate", SUBSTRATES)
def test_independent_substrates_have_different_identities(
    substrate: Callable[[], Substrate], tmp_path: Path
) -> None:
    kind = substrate()
    one = kind.open(tmp_path / "one")
    other = kind.open(tmp_path / "other")
    assert identity_of(one) != identity_of(other)


@pytest.mark.parametrize("substrate", SUBSTRATES)
def test_a_reopened_durable_substrate_keeps_its_identity(
    substrate: Callable[[], Substrate], tmp_path: Path
) -> None:
    """A store whose records survive a restart keeps its identity; one whose
    records do not must not present the same identity again, since a new
    object is a new store (the restart variant of the residual)."""
    kind = substrate()
    store = kind.open(tmp_path)
    before = identity_of(store)
    if kind.reopen is None:
        assert identity_of(kind.open(tmp_path)) != before
        return
    assert identity_of(kind.reopen(store)) == before


@pytest.mark.parametrize("substrate", SUBSTRATES)
def test_a_copied_durable_substrate_refuses_to_open(
    substrate: Callable[[], Substrate], tmp_path: Path
) -> None:
    """The copy MUST (Dave, 2026-10-09 10:54 MST): *"A copied store must refuse,
    not 'should.'"* A store that cannot detect a copy does not conform."""
    kind = substrate()
    store = kind.open(tmp_path)
    identity_of(store)
    if kind.copy is None or kind.copy_refusal is None:
        pytest.skip(f"not copyable: {kind.not_copyable}")
    with pytest.raises(kind.copy_refusal, match="copied"):
        kind.copy(store, tmp_path)
