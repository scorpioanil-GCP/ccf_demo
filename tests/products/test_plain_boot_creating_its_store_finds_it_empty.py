"""SEC-020, OWED-RULINGS-3 item 2A (b): a plain boot that creates its store must find it empty.

Dave, 2026-10-09 06:21 MST, ``D-IMPL-378``, verbatim: *"2A(b), 2B(a)"*. The option
he picked (OWED-RULINGS-3 item 2A, from lane ``378f-p4e`` §7, proposal A (b)):
*"A plain boot that created its deployment marker in this boot is creating a new
store, so it must also find it empty. One read per store creation, no Protocol
change. Reopening an existing store is unaffected. This would refuse L4's plant
the way L6's is refused now."* SEC-020 stays OPEN: these tests measure what the
SDK refuses, and nothing here closes it.

L4, measured by lane ``378f-p4e`` on ``6d3ecf30`` (``probe_p4_strict_limits.py``)
and again by this lane on ``a539c215``: a boot not for a question leaves its
deployment marker beside a path that has no store yet, and a used question
store written at that path after the marker and before the adapter opens it was
booted as the deployment's store, ``store_creation`` ``"verified"``, and a later
governed call over it was answered. L6 — the same write at a question boot's
path — is refused when that boot reads its store
(``src/ccf/deployment/manifest.py::QuestionStoreNotEmpty``).

What is asserted, by mechanism:

1. **L4 refused by name.** On the hand-composed road (``load_and_boot``) and on
   the single-file config door (``load_config_and_boot``), a plain boot that
   created its deployment marker, over a used question store written at its path
   inside the boot, raises ``DeploymentStoreNotEmpty``. The refusal holds: a
   later plain boot of the path opens a store with no marker beside it, and a
   governed call over it is refused (``UnmarkedStoreNotPresumedFresh``), so
   booting again does not turn the plant into a store the SDK vouches for.
2. **One read per store creation, none on reopening.** The boot that creates
   the store reads it once through the governed reader at the latest instant a
   timestamp can name; a boot that reopens it reads nothing there.
3. **Control: reopening an existing store is unaffected.** The deployment's own
   store, created empty and then written by its owner, boots again and answers.

The refusal is asserted by its class NAME as a string, so a tree without the
check fails each test on its behavior, never on an import. Every domain value
here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
import shutil
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.deployment import load_and_boot, load_config_and_boot
from ccf.products.resolver import ProductNotResolvable
from ccf.replay.serve import ServedProduct
from tests.products import test_question_store_empty_at_boot_and_held_through_use as p4e
from tests.products import test_withheld_subject_population_composite_and_fabric as m
from tests.support.sqlite_lease import lock_dir_beside

sec020 = m.sec020

#: The refusal this check raises, by name (absent on a tree without the check).
REFUSAL = "DeploymentStoreNotEmpty"

#: The store file every hand-composed fixture fabric here names.
_STORE = "graph.sqlite3"

#: The instant the one emptiness read is taken at: the latest a timestamp can name.
_LATEST = datetime.max.replace(tzinfo=UTC)


def _boot_plainly(manifest: pathlib.Path, registry: Any, path: pathlib.Path) -> Any:
    """A plain (not for a question) writer boot of ``path``: the fabric, or what the boot raised."""
    try:
        return load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))})
    except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
        return raised


def _later_governed_call(fabric: Any, registry: Any, records: Any) -> Any:
    """A governed call over ``fabric`` with no acquisition phase, about an identifier that names nothing."""
    try:
        return m._ask(m._governed((fabric, registry, records), plan_factory=m._late(), acquisition=None), sec020.MISSING)
    except ProductNotResolvable as raised:
        return raised


def _what_it_booted(fabric: Any, registry: Any, records: Any) -> str:
    """What a boot that should have been refused booted, and what a governed call over it met; closes the fabric."""
    try:
        held = p4e._held(fabric)
        later = _later_governed_call(fabric, registry, records)
        return (
            f"it booted (store_creation {fabric.store_creation!r}, {held} entities held for its tenant),"
            f" and a governed call over it met {type(later).__name__}"
        )
    finally:
        fabric.handle.close()


def _latest_reads(events: list[tuple[str, ...]]) -> int:
    return sum(1 for event in events if event == ("read", _LATEST.isoformat()))


# --- 1. L4, refused by name, and the refusal holds ----------------------------------------------


def test_2a_b_a_plain_boot_creating_its_store_refuses_a_store_planted_at_its_path_by_name(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L4 on the hand-composed road: refused by name when the boot reads the store it created; a reboot vouches for nothing."""
    manifest, registry, records = p4e._deployment(tmp_path)
    used = p4e._used_question_store(tmp_path, manifest, registry, records)
    target = tmp_path / "plain" / _STORE
    target.parent.mkdir()
    writer = p4e._WriteInsideTheBoot(monkeypatch, copy_of=used)
    writer.arm()

    outcome = _boot_plainly(manifest, registry, target)

    assert writer.written == [_STORE], f"the store was not planted; the case was not constructed: {writer.written}"
    if not m._named(outcome, REFUSAL):
        what = _what_it_booted(outcome, registry, records) if not isinstance(outcome, Exception) else repr(outcome)
        pytest.fail(
            "a plain boot that created its deployment marker, over a used question store written at its path"
            f" inside the boot, was not refused by name ({REFUSAL}): {what}"
        )
    assert p4e._sdk_markers(target) == [], (
        f"the refused boot must leave no marker vouching for the planted store: {p4e._sdk_markers(target)}"
    )
    again = _boot_plainly(manifest, registry, target)
    assert not isinstance(again, Exception), f"reopening the path must boot, as reopening is unaffected: {again!r}"
    try:
        assert again.store_creation == "unmarked", f"a later boot vouched for the planted store: {again.store_creation!r}"
        later = _later_governed_call(again, registry, records)
        assert m._named(later, "UnmarkedStoreNotPresumedFresh"), (
            f"a governed call over the planted store, booted again, must be refused: it met {type(later).__name__}"
        )
    finally:
        again.handle.close()


def test_2a_b_the_config_door_refuses_a_store_planted_at_a_plain_boots_path_by_name(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L4 through the single-file config door: an earlier question's store, planted inside a plain boot, is refused."""
    scratch = tmp_path / "scratch"
    with p4e._open_paved(p4e._paved_tree(tmp_path), scratch, acquire=sec020._AcquireForSubject()) as opened:
        first = m._paved_ask(opened, sec020.PAVED_WITHHELD)
        used = sorted(scratch.glob("paved_fixture*.sqlite3"))
        assert isinstance(first, ServedProduct) and len(used) == 1, f"the first question was not constructed: {first!r}"
        kept = tmp_path / "an-earlier-questions-store.sqlite3"
        shutil.copy(used[0], kept)
        target = tmp_path / "plain-config" / _STORE
        target.parent.mkdir()
        writer = p4e._WriteInsideTheBoot(monkeypatch, copy_of=kept)
        writer.arm()
        try:
            outcome: Any = load_config_and_boot(
                opened.config_path, registry=opened.control_plane, connection={"database_path": str(target), "writer_lease_lock_dir": lock_dir_beside(str(target))}
            )
        except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
            outcome = raised
        assert writer.written == [_STORE], f"the store was not planted; the case was not constructed: {writer.written}"
        if not m._named(outcome, REFUSAL):
            what = repr(outcome)
            if not isinstance(outcome, Exception):
                what = f"it booted (store_creation {outcome.store_creation!r}, {p4e._held(outcome)} entities held)"
                outcome.handle.close()
            pytest.fail(
                "a plain boot through the config door that created its deployment marker, over an earlier"
                f" question's store written at its path inside the boot, was not refused by name ({REFUSAL}): {what}"
            )
    assert p4e._sdk_markers(target) == [], f"the refused boot must leave no marker: {p4e._sdk_markers(target)}"


# --- 2. one read per store creation, none when reopening ----------------------------------------


def test_2a_b_a_plain_boot_reads_the_store_it_creates_once_and_a_reopening_boot_reads_nothing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The creating boot's one read at the latest instant, inside the boot; the reopening boot takes none."""
    manifest, registry, records = p4e._deployment(tmp_path)
    events: list[tuple[str, ...]] = []
    p4e._record_reads(monkeypatch, events)
    path = tmp_path / "fresh" / _STORE
    path.parent.mkdir()

    created = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))})
    reads_creating = _latest_reads(events)
    try:
        for envelope in m._base_accounts():
            created.handle.worker.ingest(envelope)
    finally:
        created.handle.close()
    events.clear()
    reopened = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))})
    reads_reopening = _latest_reads(events)
    reopened.handle.close()

    assert reads_creating == 1, (
        f"a plain boot that created its store read it {reads_creating} times at the latest instant inside the"
        " boot; it must read it exactly once before handing the fabric back"
    )
    assert reads_reopening == 0, (
        f"a plain boot that reopened an existing store read it {reads_reopening} times at the latest instant;"
        " reopening is unaffected"
    )


# --- 3. control: reopening an existing store is unaffected --------------------------------------


def test_2a_b_control_the_deployments_own_store_reopened_boots_and_answers(tmp_path: pathlib.Path) -> None:
    """Created empty, written by its owner after the boot, booted again: verified, holding its claims, and answering."""
    manifest, registry, records = p4e._deployment(tmp_path)
    path = tmp_path / "kept" / _STORE
    path.parent.mkdir()
    created = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))})
    try:
        assert p4e._held(created) == 0, "the store this boot created must start empty"
        for envelope in m._base_accounts():
            created.handle.worker.ingest(envelope)
    finally:
        created.handle.close()

    reopened = load_and_boot(manifest, registry=registry, connection={"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))})
    try:
        assert reopened.store_creation == "verified", reopened.store_creation
        assert p4e._held(reopened) > 0, "the reopened store must still hold what its owner wrote"
        answered = _later_governed_call(reopened, registry, records)
        assert isinstance(answered, ServedProduct), f"a deployment's own store, reopened, must answer: {answered!r}"
    finally:
        reopened.handle.close()
