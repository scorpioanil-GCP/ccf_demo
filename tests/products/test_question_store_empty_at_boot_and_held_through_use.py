# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-020 P4s-A (b) and P4s-B (a): a question's store is empty when its boot returns, and held through its use.

Dave, 2026-10-08 16:40 MST, ``D-IMPL-378`` item 3, verbatim: *"P4s-A: (b);
P4s-B: (a). Add the emptiness check and keep unverifiable stores free of
acquisition. The check must precede acquisition and remain protected by
exclusive ownership through use."* The option he picked (OWED-RULINGS-2,
item 3, P4s-A (b)): a post-boot emptiness check for question fabrics, through
the governed reader. A question store that holds anything for its tenant at
boot is refused; one read per question boot; no Protocol change. SEC-020 stays
OPEN: these tests measure what the SDK refuses, and nothing here closes it.

What was measured before this, on ``dl-378-integ`` @ ``6942dadc`` (lane
``378f-p4e``, ``probe-l6-window-6942dad.txt``): a used store written at a
question boot's path after the SDK's last check (after the boot reserved the
path exclusively and checked it again, before the adapter opens it) was booted
as that question's fabric, holding the three accounts the used store held. The
first section asks the SDK to refuse that fabric by name when its boot returns,
before any acquisition phase runs and before anything is served, on the hand-
composed road and on the paved road, with the same refusal whatever subject the
question names.

The second section proves the order: the emptiness read happens inside the
boot, strictly before the population phase, the read before acquisition and
the subject-keyed acquisition phase, and it is the first read of the store.

The third section proves what protects the check through the question's use.
From the boot's return to the question's end, a second boot for a question at
the same path, a plain writer boot, the composition root's own writer boot, a
plain read-only boot asked a governed question, and a second governed call
over the question's fabric are each refused by name, and nothing lands in the
question's store; the routes a second worker process of the deployment has are
tried from another process too, where only the store's writer lease and the
question marker stand. Measured on ``6942dadc`` (``probe-window-attempts-6942dad.txt``):
a boot for a question that is also read-only took no writer lease, and a plain
writer boot then wrote into its store while it was open. That boot is refused
by name here, before anything is registered.

Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import contextlib
import pathlib
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.deployment import load_and_boot, load_config_and_boot
from ccf.products.resolver import UNHELD_SUBJECT_PROBE, ProductNotResolvable, build_governed_resolver
from ccf.replay.engine import replay
from ccf.replay.environment import RecordedEnvironment
from ccf.replay.serve import ServedProduct
from tests.products import test_withheld_subject_population_composite_and_fabric as m
from tests.support.sqlite_lease import lock_dir_beside

sec020 = m.sec020

#: The store file every hand-composed fixture fabric here names.
_STORE = "graph.sqlite3"

#: The latest instant a timestamp can name: the instant one read must be taken
#: at to see every claim a store holds for a tenant, whenever it was observed.
_LATEST = datetime.max.replace(tzinfo=UTC)


# --- the fixture deployments ---------------------------------------------------------


def _deployment(tmp_path: pathlib.Path) -> tuple[pathlib.Path, Any, Any]:
    """The hand-composed fixture deployment's manifest, the registry it registered into, and its record store."""
    template = m._boot(tmp_path, "documents", anchor=m.FROM_DECISION, envelopes=(), for_question=False)
    template[0].handle.close()
    return tmp_path / "documents" / "manifest.yaml", template[1], template[2]


def _held(fabric: Any) -> int:
    """How many entities the fabric's store holds for its tenant, read through its governed reader at the latest instant."""
    return len(fabric.handle.reader.as_of(tenant_id=fabric.tenant_id, at=_LATEST).entities)


def _sdk_markers(store: pathlib.Path) -> list[pathlib.Path]:
    """Every marker the SDK left beside ``store``: ``<resolved store path>.ccf-*-store``."""
    resolved = store.resolve()
    return sorted(resolved.parent.glob(f"{resolved.name}.ccf-*-store"))


def _used_question_store(tmp_path: pathlib.Path, manifest: pathlib.Path, registry: Any, records: Any) -> pathlib.Path:
    """A question's store after its question: the deployment's three accounts, and the fresher claim its acquisition fetched."""
    path = tmp_path / "used" / _STORE
    path.parent.mkdir()
    fabric = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))}, for_question=True)
    try:
        for envelope in m._base_accounts():
            fabric.handle.worker.ingest(envelope)
        seam = m._RefreshWhenAsked(fabric)
        m._ask(m._governed((fabric, registry, records), plan_factory=m._late(), acquisition=seam), sec020.WITHHELD)
    finally:
        fabric.handle.close()
    assert seam.ingested == 1, f"the used store was not constructed: its question acquired {seam.ingested}"
    return path


class _WriteInsideTheBoot:
    """Writes a store at a question boot's path after the SDK's last check, before the adapter opens it (L6).

    Replaces the boot ``ccf.deployment.manifest`` calls, so the write lands
    after the reservation and its re-check, inside the boot call, on both
    doors (the paved road boots through ``load_config_and_boot``, which shares
    the manifest's spine). Armed for one boot at a time. ``copy_of`` copies a
    used store there; ``plain_boot`` creates and fills one through a plain boot
    of the same deployment instead.
    """

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        copy_of: pathlib.Path | None = None,
        plain_boot: Callable[[pathlib.Path], None] | None = None,
    ) -> None:
        import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

        self._copy_of = copy_of
        self._plain_boot = plain_boot
        self._armed = False
        self.written: list[str] = []
        real_boot = manifest_module.boot

        def boot_after_a_write(**kwargs: Any) -> Any:
            if self._armed:
                self._armed = False
                target = pathlib.Path(str(kwargs["connection"]["database_path"]))
                if self._copy_of is not None:
                    shutil.copy(self._copy_of, target)
                elif self._plain_boot is not None:
                    self._plain_boot(target)
                self.written.append(target.name)
            return real_boot(**kwargs)

        monkeypatch.setattr(manifest_module, "boot", boot_after_a_write)

    def arm(self) -> None:
        self._armed = True


def _question_over(
    manifest: pathlib.Path, registry: Any, records: Any, path: pathlib.Path, subject: str
) -> tuple[Any, list[str], int | None]:
    """Boot ``path`` for one question and ask ``subject`` through a subject-keyed acquisition seam.

    Returns the outcome (the boot's refusal, the call's refusal, or the
    answer), what the acquisition phase was asked, and how many entities the
    fabric held when its boot returned (``None`` when it never returned).
    """
    try:
        fabric = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))}, for_question=True)
    except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
        return raised, [], None
    try:
        held = _held(fabric)
        seam = m._RefreshWhenAsked(fabric)
        try:
            outcome: Any = m._ask(m._governed((fabric, registry, records), plan_factory=m._late(), acquisition=seam), subject)
        except ProductNotResolvable as raised:
            outcome = raised
        return outcome, list(seam.asked), held
    finally:
        fabric.handle.close()


class _Asked:
    """The paved road's ``acquire``, recording the subject of every question it is called for, else delegating."""

    def __init__(self, inner: Callable[[Any], Any]) -> None:
        self._inner = inner
        self.asked: list[str] = []

    def __call__(self, context: Any) -> Any:
        self.asked.append(context.request.subject)
        return self._inner(context)


def _paved_tree(tmp_path: pathlib.Path) -> pathlib.Path:
    from tests.products.test_paved_road import _write_tree  # noqa: PLC0415

    return _write_tree(tmp_path, config=sec020._paved_config(anchor=m.FROM_DECISION, seeding=m.CLASS_SEEDED))


def _open_paved(root: pathlib.Path, scratch: pathlib.Path, **overrides: Any) -> Any:
    from tests.products.test_paved_road import _open  # noqa: PLC0415

    return _open(root, scratch, **overrides)


def _assert_refused_before_acquisition(outcomes: dict[str, tuple[Any, list[str], int | None]], *, road: str) -> None:
    """Every question refused by name when its boot returned, nothing asked of the source, the same refusal for every subject."""
    for subject, (outcome, asked, held) in outcomes.items():
        if not m._named(outcome, "QuestionStoreNotEmpty"):
            pytest.fail(
                f"[{road}] a question fabric booted over a store written at its path after the SDK's last check was"
                f" not refused by name (QuestionStoreNotEmpty): it met {type(outcome).__name__}, its fabric holding"
                f" {held} entities when its boot returned, its acquisition phase asked {asked} ({subject})"
            )
        assert asked == [], f"[{road}] the acquisition phase must not run: it was asked {asked}"
    refusals = [outcome for outcome, _asked, _held in outcomes.values()]
    assert len({type(refusal) for refusal in refusals}) == 1, f"[{road}] one refusal type for every subject: {refusals!r}"
    assert len({str(refusal) for refusal in refusals}) == 1, f"[{road}] the refusal must read nothing about the subject"


# --- 1. a store written at a question boot's path is refused when the boot returns ---------


@pytest.mark.parametrize("written_by", ["copied", "plain-boot"])
def test_p4e_a_store_written_at_a_question_boots_path_is_refused_by_name_before_acquisition(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, written_by: str
) -> None:
    """The hand-composed road: a question fabric over a store written inside its boot is refused by name.

    ``copied``: a used question store copied to the path (the L6 probe's
    shape). ``plain-boot``: the deployment's own plain boot of the same path,
    run inside the question boot, creating and filling the store. Measured on
    ``6942dadc``: the question fabric booted over it, holding 3 entities, and
    answered. Asked about the withheld account and about an identifier that
    names nothing, each question must meet the same refusal before its
    acquisition phase runs.
    """
    manifest, registry, records = _deployment(tmp_path)

    def fill_through_a_plain_boot(target: pathlib.Path) -> None:
        fabric = load_and_boot(manifest, registry=registry, connection={"database_path": str(target), "writer_lease_lock_dir": lock_dir_beside(str(target))})
        try:
            for envelope in m._base_accounts():
                fabric.handle.worker.ingest(envelope)
        finally:
            fabric.handle.close()

    if written_by == "copied":
        writer = _WriteInsideTheBoot(monkeypatch, copy_of=_used_question_store(tmp_path, manifest, registry, records))
    else:
        writer = _WriteInsideTheBoot(monkeypatch, plain_boot=fill_through_a_plain_boot)
    outcomes: dict[str, tuple[Any, list[str], int | None]] = {}
    for position, subject in enumerate((sec020.WITHHELD, sec020.MISSING)):
        path = tmp_path / f"question-{position}" / _STORE
        path.parent.mkdir()
        writer.arm()
        outcomes[subject] = _question_over(manifest, registry, records, path, subject)
    assert writer.written == [_STORE, _STORE], f"[{written_by}] the store was not written; the case was not constructed"
    _assert_refused_before_acquisition(outcomes, road=f"by hand, {written_by}")


def test_p4e_the_paved_road_refuses_a_store_written_at_its_question_boots_path_before_acquisition(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The paved road: a question's minted path, written with an earlier question's store inside its boot, is refused.

    The first question is answered over the store the paved road minted for
    it, and its acquisition writes the withheld account there. A copy of that
    store is written at each later question's minted path inside its boot.
    Each later question, about the withheld account or about an identifier
    that names nothing, must meet the same refusal by name before ``acquire``
    is called.
    """
    acquire = _Asked(sec020._AcquireForSubject())
    scratch = tmp_path / "scratch"
    outcomes: dict[str, tuple[Any, list[str], int | None]] = {}
    with _open_paved(_paved_tree(tmp_path), scratch, acquire=acquire) as opened:
        first = m._paved_ask(opened, sec020.PAVED_WITHHELD)
        used = sorted(scratch.glob("paved_fixture*.sqlite3"))
        assert isinstance(first, ServedProduct) and len(used) == 1, f"the first question was not constructed: {first!r}"
        kept = tmp_path / "an-earlier-questions-store.sqlite3"
        shutil.copy(used[0], kept)
        writer = _WriteInsideTheBoot(monkeypatch, copy_of=kept)
        for subject in (sec020.PAVED_WITHHELD, sec020.PAVED_ABSENT):
            already = len(acquire.asked)
            writer.arm()
            try:
                outcome: Any = m._paved_ask(opened, subject)
            except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
                outcome = raised
            outcomes[subject] = (outcome, acquire.asked[already:], None)
    assert len(writer.written) == 2, f"the stores were not written; the case was not constructed: {writer.written}"
    _assert_refused_before_acquisition(outcomes, road="the paved road")


# --- 2. the emptiness read comes first --------------------------------------------------


def _record_reads(monkeypatch: pytest.MonkeyPatch, events: list[tuple[str, ...]]) -> None:
    """Record every read through a booted fabric's governed reader, in order, with the instant it was taken at."""
    from ccf.graph import governed_reader as governed  # noqa: PLC0415

    reader_class = governed._ClassificationGovernedReader
    as_of, query = reader_class.as_of, reader_class.query

    def recorded_as_of(self: Any, *, tenant_id: str, at: datetime) -> Any:
        events.append(("read", at.isoformat()))
        return as_of(self, tenant_id=tenant_id, at=at)

    def recorded_query(self: Any, q: Any) -> Any:
        events.append(("query", q.as_of.isoformat()))
        return query(self, q)

    monkeypatch.setattr(reader_class, "as_of", recorded_as_of)
    monkeypatch.setattr(reader_class, "query", recorded_query)


class _RecordingSeam:
    """A hand-composed subject-keyed acquisition phase that records when it is called and fetches nothing."""

    def __init__(self, events: list[tuple[str, ...]]) -> None:
        self._events = events

    def __call__(self, *, request: Any, perspective: Any) -> None:
        self._events.append(("acquisition",))


class _RecordingPopulation:
    """A hand-composed population phase that records when it is called and fetches nothing."""

    def __init__(self, events: list[tuple[str, ...]]) -> None:
        self._events = events

    def __call__(self, *, question: Any, perspective: Any) -> None:
        self._events.append(("population",))


class _RecordingPavedAcquire:
    """The paved road's ``acquire``, recording when it is called, else the subject-keyed fixture source."""

    def __init__(self, events: list[tuple[str, ...]]) -> None:
        self._events = events
        self._inner = sec020._AcquireForSubject()

    def __call__(self, context: Any) -> Any:
        self._events.append(("acquisition",))
        return self._inner(context)


class _RecordingPavedPopulation:
    """The paved road's declared population phase, recording when it is called and fetching nothing."""

    def __init__(self, events: list[tuple[str, ...]]) -> None:
        self._events = events

    def __call__(self, context: Any) -> tuple[Any, ...]:
        self._events.append(("population",))
        return ()


def _assert_the_emptiness_read_came_first(events: list[tuple[str, ...]], outcome: Any, *, road: str) -> None:
    """The one read at the latest instant ran inside the boot, first, before the population and acquisition phases."""
    assert isinstance(outcome, ServedProduct), f"[{road}] control: a fresh question store must answer its one question: {outcome!r}"
    latest = ("read", _LATEST.isoformat())
    emptiness = [position for position, event in enumerate(events) if event == latest]
    returned = events.index(("boot returned",))
    if not emptiness or emptiness[0] > returned:
        pytest.fail(
            f"[{road}] no read of the question's store at the latest instant ran inside its boot, so nothing"
            f" checked that the store held nothing for its tenant before acquisition. Events: {events}"
        )
    reads = [position for position, event in enumerate(events) if event[0] in ("read", "query")]
    assert len(emptiness) == 1, f"[{road}] one emptiness read per question boot: {events}"
    assert emptiness[0] == reads[0], f"[{road}] the emptiness read must be the first read of the store: {events}"
    population, acquisition = events.index(("population",)), events.index(("acquisition",))
    assert emptiness[0] < returned < population < acquisition, f"[{road}] out of order: {events}"
    before_acquisition = [position for position in reads if position > returned and position < acquisition]
    assert before_acquisition, f"[{road}] the read before acquisition was not observed: {events}"


def test_p4e_the_emptiness_read_precedes_acquisition_by_hand(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The hand-composed road: the emptiness read is inside the boot and precedes every phase that acquires."""
    manifest, registry, records = _deployment(tmp_path)
    events: list[tuple[str, ...]] = []
    _record_reads(monkeypatch, events)
    path = tmp_path / "question" / _STORE
    path.parent.mkdir()
    fabric = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))}, for_question=True)
    events.append(("boot returned",))
    try:
        outcome = m._ask(
            m._governed(
                (fabric, registry, records), plan_factory=m._late(),
                acquisition=_RecordingSeam(events), population_acquisition=_RecordingPopulation(events),
            ),
            sec020.MISSING,
        )
    finally:
        fabric.handle.close()
    _assert_the_emptiness_read_came_first(events, outcome, road="by hand")


def test_p4e_the_emptiness_read_precedes_acquisition_on_the_paved_road(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The paved road: the emptiness read is inside the question's boot and precedes ``population`` and ``acquire``."""
    from ccf.products import product as product_module  # noqa: PLC0415

    events: list[tuple[str, ...]] = []
    _record_reads(monkeypatch, events)
    real_boot = product_module.load_config_and_boot

    def boot_and_record(*args: Any, **kwargs: Any) -> Any:
        fabric = real_boot(*args, **kwargs)
        events.append(("boot returned",))
        return fabric

    monkeypatch.setattr(product_module, "load_config_and_boot", boot_and_record)
    with _open_paved(
        _paved_tree(tmp_path), tmp_path / "scratch",
        acquire=_RecordingPavedAcquire(events), population=_RecordingPavedPopulation(events),
    ) as opened:
        outcome = m._paved_ask(opened, sec020.PAVED_WITHHELD)
    _assert_the_emptiness_read_came_first(events, outcome, road="the paved road")


# --- 3. exclusive ownership from the emptiness check through the question's use ---------------


def test_p4e_a_boot_for_a_question_that_would_hold_no_writer_lease_is_refused_by_name_load_and_boot(
    tmp_path: pathlib.Path,
) -> None:
    """A read-only boot for a question takes no writer lease: refused by name, before anything is registered.

    Measured on ``6942dadc`` (``probe-window-attempts-6942dad.txt``): such a
    boot was accepted, and a plain writer boot of the same path then wrote the
    deployment's three accounts into the store while the question's fabric was
    open and read them back. Nothing then held the store for the question
    between its emptiness check and its end.
    """
    manifest, registry, _records = _deployment(tmp_path)
    path = tmp_path / "read-only-question" / _STORE
    path.parent.mkdir()
    audited = len(registry.audit_events())
    try:
        fabric = load_and_boot(
            manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))}, for_question=True, read_only=True,
        )
    except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
        refused: BaseException = raised
    else:
        try:
            scope = fabric.handle.lease_scope
            other = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))})
            try:
                for envelope in m._base_accounts():
                    other.handle.worker.ingest(envelope)
            finally:
                other.handle.close()
            held = _held(fabric)
        finally:
            fabric.handle.close()
        pytest.fail(
            f"a boot for a question that holds no writer lease was booted (lease scope {scope!r}); a plain writer"
            f" boot of its path then wrote into its store while it was open, and it read back {held} entities. It"
            " must be refused by name (QuestionFabricNotExclusive) before anything is registered"
        )
    assert m._named(refused, "QuestionFabricNotExclusive"), f"refused, but for another reason: {refused!r}"
    assert len(registry.audit_events()) == audited, "nothing may be registered before the refusal"
    assert not path.exists() and not _sdk_markers(path), "nothing may be created at the path before the refusal"


def test_p4e_a_boot_for_a_question_that_would_hold_no_writer_lease_is_refused_by_name_load_config_and_boot(
    tmp_path: pathlib.Path,
) -> None:
    """The single-file door (the paved road's): the same refusal, before anything is registered."""
    with _open_paved(_paved_tree(tmp_path), tmp_path / "scratch", acquire=sec020._AcquireForSubject()) as opened:
        path = tmp_path / "read-only-question.sqlite3"
        audited = len(opened.control_plane.audit_events())
        try:
            fabric = load_config_and_boot(
                opened.config_path, registry=opened.control_plane, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))},
                for_question=True, read_only=True,
            )
        except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
            refused: BaseException = raised
        else:
            scope = fabric.handle.lease_scope
            fabric.handle.close()
            pytest.fail(
                f"a boot for a question that holds no writer lease was booted (lease scope {scope!r}); it must be"
                " refused by name (QuestionFabricNotExclusive) before anything is registered"
            )
        assert len(opened.control_plane.audit_events()) == audited, "nothing may be registered before the refusal"
    assert m._named(refused, "QuestionFabricNotExclusive"), f"refused, but for another reason: {refused!r}"
    assert not path.exists() and not _sdk_markers(path), "nothing may be created at the path before the refusal"


class _Routes:
    """Every route into a question's store a deployment has, each tried at a named moment of the question's use."""

    def __init__(self, attempts: dict[str, Callable[[], Any]]) -> None:
        self._attempts = attempts
        self.outcomes: dict[tuple[str, str], Any] = {}

    def run(self, moment: str, *, skip: tuple[str, ...] = ()) -> None:
        for route, attempt in self._attempts.items():
            if route in skip:
                continue
            try:
                self.outcomes[(moment, route)] = attempt()
            except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
                self.outcomes[(moment, route)] = raised


def _during(subject: str) -> str:
    """The moment one acquisition call's tries are kept under: the subject that call was handed."""
    return f"during its acquisition phase, handed {subject}"


class _TryingSeam:
    """A hand-composed acquisition phase that tries every route while the question is using its store, in every call.

    ``D-IMPL-378`` ruling P6 (a) (Q10 amended to permit the probe): a class that
    may withhold late and declares no early policy hands this phase the probe
    identifier first, then the question's subject. Each call is part of the
    question's use, so each call's tries are kept under the subject it was
    handed (``handed``, in order), and, given ``read_held``, what the
    question's store holds is read after each call's tries (``held``).
    """

    def __init__(self, routes: _Routes, *, read_held: Callable[[], int] | None = None) -> None:
        self._routes = routes
        self._read_held = read_held
        self.handed: list[str] = []
        self.held: list[int] = []

    def __call__(self, *, request: Any, perspective: Any) -> None:
        self.handed.append(request.subject)
        self._routes.run(_during(request.subject))
        if self._read_held is not None:
            self.held.append(self._read_held())


def _governed_call(fabric: Any, registry: Any, records: Any) -> Any:
    """A governed question with no acquisition phase over ``fabric``: what a door asks of a store it opened."""
    return m._ask(m._governed((fabric, registry, records), plan_factory=m._late(), acquisition=None), sec020.MISSING)


def _assert_each_acquisition_call_tried_and_refused_every_route(
    routes: _Routes, handed: list[str], expected: dict[str, str], *, road: str
) -> None:
    """Every route tried in every acquisition call, in the order the calls were made, each refused by its own name."""
    for subject in handed:
        in_call = {route: outcome for (moment, route), outcome in routes.outcomes.items() if moment == _during(subject)}
        assert set(in_call) == set(expected), (
            f"[{road}] not every route was tried in the acquisition call handed {subject}: {sorted(in_call)}"
        )
        for route, outcome in in_call.items():
            assert m._named(outcome, expected[route]), (
                f"[{road}] {route}, {_during(subject)}, was not refused by name ({expected[route]}): {outcome!r}"
            )


def _assert_every_route_refused_by_name(routes: _Routes, expected: dict[str, str], *, road: str) -> None:
    tried = {route for _moment, route in routes.outcomes}
    assert tried == set(expected), f"[{road}] not every route was tried: {sorted(tried)}"
    for (moment, route), outcome in routes.outcomes.items():
        assert m._named(outcome, expected[route]), (
            f"[{road}] {route}, {moment}, was not refused by name ({expected[route]}): {outcome!r}"
        )


def test_p4e_nothing_claims_opens_or_writes_a_question_store_from_its_emptiness_check_to_its_end_by_hand(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exclusive ownership through use, the hand-composed road: every other route is refused by name, nothing lands.

    Each route is tried after the boot returned (its emptiness check done)
    and again while the question's acquisition phase runs. The question's
    fabric holds the writer lease (cross-process), its path carries the
    question marker created exclusively, and the fabric is claimed by the
    question's governed call. A second governed call is tried only once the
    first has claimed the fabric.

    ``D-IMPL-378`` ruling P6 (a) (Q10 amended to permit the probe): the
    acquisition phase is called twice, handed the probe identifier first and
    then the question's subject; both calls are part of the question's use, so
    every route is tried and judged in each, and nothing may land in either.
    """
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    manifest, registry, records = _deployment(tmp_path)
    path = tmp_path / "question" / _STORE
    path.parent.mkdir()
    captured: dict[str, Any] = {}
    real_boot = manifest_module.boot

    def capture(**kwargs: Any) -> Any:
        captured.setdefault("kwargs", dict(kwargs))
        return real_boot(**kwargs)

    monkeypatch.setattr(manifest_module, "boot", capture)
    question = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))}, for_question=True)
    connection = {"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))}

    def a_question_boot() -> Any:
        load_and_boot(manifest, registry=registry, connection=connection, for_question=True).handle.close()
        return "booted"

    def a_plain_writer_boot() -> Any:
        fabric = load_and_boot(manifest, registry=registry, connection=connection)
        try:
            for envelope in m._base_accounts():
                fabric.handle.worker.ingest(envelope)
        finally:
            fabric.handle.close()
        return "booted and wrote"

    def a_plain_read_only_boot_asked_a_question() -> Any:
        fabric = load_and_boot(manifest, registry=registry, connection=connection, read_only=True)
        try:
            return _governed_call(fabric, registry, records)
        finally:
            fabric.handle.close()

    def the_composition_roots_writer_boot() -> Any:
        real_boot(**{**captured["kwargs"], "connection": connection, "read_only": False}).close()
        return "booted"

    def a_second_governed_call() -> Any:
        return _governed_call(question, registry, records)

    routes = _Routes(
        {
            "a boot for a question at its path": a_question_boot,
            "a plain writer boot at its path": a_plain_writer_boot,
            "a plain read-only boot at its path, asked a governed question": a_plain_read_only_boot_asked_a_question,
            "ccf.boot.boot booting a writer over its path": the_composition_roots_writer_boot,
            "a second governed call over the question's fabric": a_second_governed_call,
        }
    )
    seam = _TryingSeam(routes, read_held=lambda: _held(question))
    try:
        routes.run("after its boot returned", skip=("a second governed call over the question's fabric",))
        outcome = m._ask(
            m._governed((question, registry, records), plan_factory=m._late(), acquisition=seam),
            sec020.MISSING,
        )
        held = _held(question)
    finally:
        question.handle.close()
    assert isinstance(outcome, ServedProduct), f"the question itself must be answered: {outcome!r}"
    expected = {
        "a boot for a question at its path": "QuestionFabricNotFresh",
        "a plain writer boot at its path": "SingleWriterViolation",
        "a plain read-only boot at its path, asked a governed question": "QuestionStoreReopened",
        "ccf.boot.boot booting a writer over its path": "SingleWriterViolation",
        "a second governed call over the question's fabric": "AcquiredFabricReused",
    }
    # P6 (a): the probe's call, then the subject's, each once; every route tried and judged in each, the probe's first.
    assert seam.handed == [UNHELD_SUBJECT_PROBE, sec020.MISSING], (
        "[by hand] the routes were not tried in every acquisition call; the case was not constructed: the phase"
        f" was handed {seam.handed}"
    )
    _assert_each_acquisition_call_tried_and_refused_every_route(routes, seam.handed, expected, road="by hand")
    _assert_every_route_refused_by_name(routes, expected, road="by hand")
    assert seam.held == [0, 0], f"nothing any route tried may land in the question's store, in either call: {seam.held}"
    assert held == 0, f"nothing any route tried may land in the question's store: it holds {held} entities"


def test_p4e_nothing_claims_opens_or_writes_a_question_store_from_its_emptiness_check_to_its_end_on_the_paved_road(
    tmp_path: pathlib.Path,
) -> None:
    """Exclusive ownership through use, the paved road: tried from inside ``acquire``, through the single-file door.

    ``D-IMPL-378`` ruling P6 (a) (Dave, 2026-10-08 16:40 MST: *"Amend Q10 to
    permit the probe"*): this class may withhold late and declares no early
    policy, so ``acquire`` is called twice for its one question, handed the
    probe identifier first and then the question's subject. Both calls are
    inside the question's use, so the routes are tried in each call and judged
    in each, and nothing may land in the store in either.
    """
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415
    from tests.products.test_paved_road import ASKED_AT as PAVED_ASKED_AT  # noqa: PLC0415

    scratch = tmp_path / "scratch"
    held: list[int] = []
    routes_holder: list[_Routes] = []
    handed: list[str] = []

    class _TryingAcquire:
        def __init__(self) -> None:
            self._inner = sec020._AcquireForSubject()

        def __call__(self, context: Any) -> Any:
            handed.append(context.request.subject)
            minted = sorted(scratch.glob("paved_fixture*.sqlite3"))
            assert len(minted) == 1, minted
            connection = {"database_path": str(minted[0]), "writer_lease_lock_dir": lock_dir_beside(str(minted[0]))}

            def a_question_boot() -> Any:
                load_config_and_boot(
                    opened.config_path, registry=opened.control_plane, connection=connection, for_question=True,
                ).handle.close()
                return "booted"

            def a_plain_writer_boot() -> Any:
                fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection=connection)
                fabric.handle.close()
                return "booted"

            def a_plain_read_only_boot_asked_a_question() -> Any:
                fabric = load_config_and_boot(
                    opened.config_path, registry=opened.control_plane, connection=connection, read_only=True,
                )
                try:
                    arguments = opened.build_arguments(fabric)
                    arguments["acquisition"] = None
                    return build_governed_resolver(**arguments)(
                        tenant=opened.tenant_id, product_class=opened.declaration.schema_name,
                        version=opened.declaration.schema_version, perspective=opened.default_perspective,
                        request=opened.question(
                            subject=sec020.PAVED_ABSENT, asked_at=PAVED_ASKED_AT, intent="fixture-intent",
                            freshness="fixture-freshness", parameters={PAVED_THRESHOLD: 1000},
                        ),
                    )
                finally:
                    fabric.handle.close()

            routes = _Routes(
                {
                    "a boot for a question at its path": a_question_boot,
                    "a plain writer boot at its path": a_plain_writer_boot,
                    "a plain read-only boot at its path, asked a governed question": a_plain_read_only_boot_asked_a_question,
                }
            )
            routes.run(f"during its acquisition phase, handed {context.request.subject}")
            routes_holder.append(routes)
            reader = load_config_and_boot(
                opened.config_path, registry=opened.control_plane, connection=connection, read_only=True,
            )
            try:
                held.append(_held(reader))
            finally:
                reader.handle.close()
            return self._inner(context)

    with _open_paved(_paved_tree(tmp_path), scratch, acquire=_TryingAcquire()) as opened:
        outcome = m._paved_ask(opened, sec020.PAVED_WITHHELD)
    assert isinstance(outcome, ServedProduct), f"the question itself must be answered: {outcome!r}"
    # P6 (a): the probe's call, then the subject's, each once; the routes tried in both.
    assert handed == [UNHELD_SUBJECT_PROBE, sec020.PAVED_WITHHELD] and len(routes_holder) == len(handed), (
        "the routes were not tried in every acquisition call; the case was not constructed:"
        f" acquire was handed {handed}, the routes were tried {len(routes_holder)} time(s)"
    )
    for routes in routes_holder:
        _assert_every_route_refused_by_name(
            routes,
            {
                "a boot for a question at its path": "QuestionFabricNotFresh",
                "a plain writer boot at its path": "SingleWriterViolation",
                "a plain read-only boot at its path, asked a governed question": "QuestionStoreReopened",
            },
            road="the paved road",
        )
    assert held == [0, 0], f"nothing any route tried may land in the question's store, in either call: {held}"


class _AnotherProcess:
    """A hand-composed acquisition phase that runs another process's routes into the store while the question uses it.

    ``D-IMPL-378`` ruling P6 (a) (Q10 amended to permit the probe): the phase is
    handed the probe identifier first, then the question's subject. Each call is
    part of the question's use, so each call's report from the other process is
    kept under the subject that call was handed (``calls``, in order), and,
    given ``read_held``, what the question's store holds is read after each
    call's run (``held``).
    """

    def __init__(
        self, manifest: pathlib.Path, path: pathlib.Path, records: pathlib.Path,
        *, read_held: Callable[[], int] | None = None,
    ) -> None:
        self._arguments = (str(manifest), str(path), str(records))
        self._read_held = read_held
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.held: list[int] = []

    def __call__(self, *, request: Any, perspective: Any) -> None:
        import json  # noqa: PLC0415
        import os  # noqa: PLC0415
        import subprocess  # noqa: PLC0415
        import sys  # noqa: PLC0415

        root = pathlib.Path(__file__).resolve().parents[2]
        estate = ("PG", "FLUREE_", "MONGO_", "NEO4J_", "CO_LENDER_")
        environment = {key: value for key, value in os.environ.items() if not key.startswith(estate)}
        environment["PYTHONPATH"] = os.pathsep.join(str(root / part) for part in ("src", "runtime"))
        ran = subprocess.run(
            [sys.executable, "-B", "-m", "tests.products._question_store_routes_from_another_process", *self._arguments],
            cwd=root, env=environment, capture_output=True, text=True, timeout=300, check=False,
        )
        assert ran.returncode == 0, f"the other process did not run: {ran.stderr[-2000:]}"
        self.calls.append((request.subject, json.loads(ran.stdout.strip().splitlines()[-1])))
        if self._read_held is not None:
            self.held.append(self._read_held())


def test_p4e_from_another_process_nothing_claims_opens_or_writes_a_question_store_during_its_use(
    tmp_path: pathlib.Path,
) -> None:
    """Exclusive ownership through use, across processes: the routes another worker process has are refused by name.

    In one process a second writer is refused by the process's live-writer
    table before the store's writer lease is asked; across processes, only
    the lease (a ``flock`` beside the SQLite file) and the question marker
    stand. A second process of the same deployment, with its own Control
    Plane registry built from the same documents, tries each route while the
    question's acquisition phase runs: a boot for a question at the path, a
    plain writer boot that would write the deployment's three accounts, and a
    plain read-only boot asked a governed question.

    ``D-IMPL-378`` ruling P6 (a) (Q10 amended to permit the probe): the
    acquisition phase is called twice, handed the probe identifier first and
    then the question's subject; both calls are part of the question's use, so
    the other process tries every route in each, each call is judged, and
    nothing may land in either.
    """
    manifest, registry, records = _deployment(tmp_path)
    path = tmp_path / "question" / _STORE
    path.parent.mkdir()
    other_records = tmp_path / "other-process-records"
    question = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))}, for_question=True)
    seam = _AnotherProcess(manifest, path, other_records, read_held=lambda: _held(question))
    try:
        outcome = m._ask(m._governed((question, registry, records), plan_factory=m._late(), acquisition=seam), sec020.MISSING)
        held = _held(question)
    finally:
        question.handle.close()
    assert isinstance(outcome, ServedProduct), f"the question itself must be answered: {outcome!r}"
    # P6 (a): the probe's call, then the subject's, each once; each call's report judged, the probe's first.
    handed = [subject for subject, _report in seam.calls]
    assert handed == [UNHELD_SUBJECT_PROBE, sec020.MISSING], (
        "the other process's routes were not tried in every acquisition call; the case was not constructed: the"
        f" phase was handed {handed}"
    )
    root = pathlib.Path(__file__).resolve().parents[2]
    expected = {
        "a boot for a question at its path": "QuestionFabricNotFresh",
        "a plain writer boot at its path": "SingleWriterViolation",
        "a plain read-only boot at its path, asked a governed question": "QuestionStoreReopened",
    }
    for subject, report in seam.calls:
        imported = pathlib.Path(report.get("imported", ""))
        assert imported.is_relative_to(root / "src"), f"the other process measured another tree: {imported}"
        for route, name in expected.items():
            found = report.get(route, {})
            assert name in found.get("raised", []), (
                f"from another process, {route}, {_during(subject)}, was not refused by name ({name}): {found}"
            )
    assert seam.held == [0, 0], (
        f"nothing another process tried may land in the question's store, in either call: {seam.held}"
    )
    assert held == 0, f"nothing another process tried may land in the question's store: it holds {held} entities"


# --- controls ----------------------------------------------------------------------------


def test_p4e_control_a_record_served_over_a_fresh_question_store_replays_to_its_own_address(tmp_path: pathlib.Path) -> None:
    """Decision Replay reads a question's store through a read-only boot that is not for a question: unaffected."""
    scratch = tmp_path / "scratch"
    with contextlib.ExitStack() as stack:
        opened = stack.enter_context(_open_paved(_paved_tree(tmp_path), scratch, acquire=sec020._AcquireForSubject()))
        served = m._paved_ask(opened, sec020.PAVED_WITHHELD)
        assert isinstance(served, ServedProduct), served
        record = opened.record_of(served)
        minted = sorted(scratch.glob("paved_fixture*.sqlite3"))
        assert len(minted) == 1, minted
        fabric = load_config_and_boot(
            opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted[0]), "writer_lease_lock_dir": lock_dir_beside(str(minted[0]))},
            read_only=True,
        )
        stack.callback(fabric.handle.close)
        outcome = replay(
            record_address=served.replay_ref.content_address, store=opened.artifact_store,
            reader=fabric.handle.reader, control_plane=opened.control_plane,
            environment=RecordedEnvironment(record=record, opened=opened, fabric=fabric),
        )
    path = record.content_generation_path
    assert content_hash(outcome.product) == path.product_content_address == content_hash(served.product), (
        "a record served over a fresh question store must replay to its own address"
    )
