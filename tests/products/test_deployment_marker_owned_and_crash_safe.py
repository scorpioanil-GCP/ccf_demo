"""SEC-020, D-IMPL-378 repair 1.1: the deployment marker a plain boot creates is removed on every failed boot, and is crash-safe.

Dave, 2026-10-09 10:54 MST, verbatim: *"Remove markers created by this boot on
every failed-boot path, including failure during close. Remove only markers this
boot owns. A marker left by a crash must not imply completed verification."*
SEC-020 stays OPEN: these tests measure what the SDK refuses, and nothing here
closes it.

What was measured before the repair, on ``dl-378-integ`` @ ``fe25536c`` (the
panel's Fable G2 F-G2-1 and the CLI panel's G-2AB-CLOSE-ORDER, re-run by lane
``378j-boot``): ``src/ccf/deployment/manifest.py::_register_and_boot`` removed
the deployment markers it created only when its emptiness read raised. A plain
boot whose ``boot()`` failed after the marker existed (a planted store given a
second name, refused at open as ``WriterLeaseHeld``; or the planted store's
writer lease held elsewhere, refused at the mint as ``SingleWriterViolation``),
or whose ``close()`` raised while it cleaned up, left its marker; the retry was a
reopen, took no read, booted the planted store with ``store_creation``
``"verified"``, and a governed call over it was answered. A marker records
nothing about whether its boot's read completed, so a boot killed between the
marker and the read left one that every later boot read as ``"verified"``.

What is asserted, by mechanism:

1. **Every failed boot removes the marker it created** — a failure inside
   ``boot()`` (``WriterLeaseHeld``, ``SingleWriterViolation``, an interrupt),
   and a ``close()`` that raises while the read's refusal is cleaned up — and
   the retry over the planted store is refused by name
   (``UnmarkedStoreNotPresumedFresh``) at its governed call.
2. **Only markers this boot owns.** A marker that is no longer the one this boot
   created — replaced by another file, or rewritten in place — is left where it
   is.
3. **Crash-safe.** A marker reads ``pending`` until the boot's emptiness read has
   completed and ``verified`` only after; a boot killed (``SIGKILL``, in another
   process) before its read completes leaves a ``pending`` marker, and every
   later boot of the path, writer or read-only, is refused by name
   (``DeploymentMarkerUnresolved``, reason ``pending``) and leaves the marker
   for an operator.
4. **A marker that cannot show a completed verification is never read as one**:
   the single-line marker this tree wrote before the repair, a marker whose text
   is not the SDK's, and a symbolic link at the marker's path are each refused by
   name (reason ``unreadable``) and left untouched.

Refusals are asserted by their class NAME and their ``reason``, so a tree
without the repair fails each test on its behavior, never on an import. Every
domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import fcntl
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
from typing import Any

import pytest

from ccf.deployment import load_and_boot
from tests.products import test_plain_boot_creating_its_store_finds_it_empty as tp
from tests.products import test_question_store_empty_at_boot_and_held_through_use as p4e
from tests.products import test_withheld_subject_population_composite_and_fabric as m

#: The refusal a boot meets over a marker that does not show a completed verification (absent on a tree without it).
UNRESOLVED = "DeploymentMarkerUnresolved"

#: The store file every hand-composed fixture fabric here names.
_STORE = "graph.sqlite3"

#: What a plain boot appends to the resolved store path to name its marker (fragment 378-34).
_DEPLOYMENT_MARKER_SUFFIX = ".ccf-deployment-store"

#: The SQLite writer lease's sidecar suffix (``src/ccf/graph/backends/sqlite.py::WRITER_LEASE_SUFFIX``).
_WRITER_LEASE_SUFFIX = ".ccf-writer.lock"

#: The one line every deployment marker read before this repair, verbatim (``fe25536c``).
_SINGLE_LINE_MARKER = (
    "created by a boot not for a question; no acquisition phase writes into it (SEC-020, D-IMPL-378)\n"
)


def _marker(store: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(f"{store.resolve()}{_DEPLOYMENT_MARKER_SUFFIX}")


def _state(marker: pathlib.Path) -> str | None:
    """The ``state:`` a deployment marker records, or ``None`` when it records none."""
    for line in marker.read_text(encoding="utf-8").splitlines():
        if line.startswith("state: "):
            return line.removeprefix("state: ")
    return None


def _plant_inside_the_boot(monkeypatch: pytest.MonkeyPatch, used: pathlib.Path, then: Any = None) -> list[str]:
    """Write a used store at the boot's path after its marker and before the adapter opens it; then run ``then``.

    Replaces the boot ``ccf.deployment.manifest`` calls, once: the plant lands
    inside the boot call, after every check the boot made at its path. ``then``
    (given the store path) makes ``boot()`` fail the way the case needs.
    """
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    real_boot = manifest_module.boot
    planted: list[str] = []

    def plant_then_boot(**kwargs: Any) -> Any:
        if not planted:
            target = pathlib.Path(str(kwargs["connection"]["database_path"]))
            shutil.copy(used, target)
            planted.append(target.name)
            if then is not None:
                then(target)
        return real_boot(**kwargs)

    monkeypatch.setattr(manifest_module, "boot", plant_then_boot)
    return planted


def _refused_at_its_governed_call(again: Any, registry: Any, records: Any) -> str:
    """The retry booted: what its ``store_creation`` was and what a governed call over it met; closes it."""
    try:
        later = tp._later_governed_call(again, registry, records)
        return f"store_creation {again.store_creation!r}; a governed call over it met {type(later).__name__}"
    finally:
        again.handle.close()


# --- 1. every failed boot removes the marker it created --------------------------------------------------------


class _HeldLease:
    """Another holder of the planted store's writer lease: an exclusive ``flock`` on its sidecar."""

    def __init__(self) -> None:
        self.descriptor: int | None = None

    def __call__(self, target: pathlib.Path) -> None:
        sidecar = pathlib.Path(f"{target.resolve()}{_WRITER_LEASE_SUFFIX}")
        self.descriptor = os.open(sidecar, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def release(self) -> None:
        if self.descriptor is not None:
            fcntl.flock(self.descriptor, fcntl.LOCK_UN)
            os.close(self.descriptor)
            self.descriptor = None


@pytest.mark.parametrize(
    ("failure", "raised_as"),
    [
        ("a second name for the planted store", "WriterLeaseHeld"),
        ("the planted store's writer lease held elsewhere", "SingleWriterViolation"),
        ("an interrupt inside the boot", "KeyboardInterrupt"),
    ],
)
def test_1_1_a_boot_that_fails_inside_boot_leaves_no_marker_and_the_retry_over_the_plant_is_refused(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, failure: str, raised_as: str
) -> None:
    """F-G2-1: ``boot()`` fails after the marker exists; no marker survives, and the retry vouches for nothing.

    The plant lands inside the boot, after the marker and before the adapter
    opens the store; then ``boot()`` fails. Measured on ``fe25536c``: the marker
    stayed, the retry reopened the planted store ``"verified"`` with no read, and
    a governed call over it was answered (``ServedProduct``).
    """
    manifest, registry, records = p4e._deployment(tmp_path)
    used = p4e._used_question_store(tmp_path, manifest, registry, records)
    target = tmp_path / "plain" / _STORE
    target.parent.mkdir()
    link = target.with_name(f"{_STORE}.second-name")
    held = _HeldLease()

    def fail(planted_at: pathlib.Path) -> None:
        if raised_as == "WriterLeaseHeld":
            os.link(planted_at, link)
        elif raised_as == "SingleWriterViolation":
            held(planted_at)
        else:
            raise KeyboardInterrupt(failure)

    planted = _plant_inside_the_boot(monkeypatch, used, then=fail)
    try:
        outcome: Any = tp._boot_plainly(manifest, registry, target)
    except KeyboardInterrupt as interrupted:  # not an Exception: `_boot_plainly` lets it through
        outcome = interrupted
    finally:
        link.unlink(missing_ok=True)  # the attacker takes the trigger away again
        held.release()
    assert planted == [_STORE], f"the store was not planted; the case was not constructed: {planted}"
    if not isinstance(outcome, BaseException):
        outcome.handle.close()
        pytest.fail(f"[{failure}] the boot was meant to fail inside boot(); it booted: the case was not constructed")
    assert m._named(outcome, raised_as), f"[{failure}] boot() failed, but not as constructed: {outcome!r}"
    assert p4e._sdk_markers(target) == [], (
        f"[{failure}] a boot that failed inside boot() left the marker it created beside the planted store:"
        f" {[marker.name for marker in p4e._sdk_markers(target)]}"
    )
    again = tp._boot_plainly(manifest, registry, target)
    assert not isinstance(again, Exception), f"[{failure}] the retry must boot the unmarked store: {again!r}"
    try:
        assert again.store_creation == "unmarked", (
            f"[{failure}] the retry vouched for the planted store: store_creation {again.store_creation!r}"
        )
        later = tp._later_governed_call(again, registry, records)
        assert m._named(later, "UnmarkedStoreNotPresumedFresh"), (
            f"[{failure}] a governed call over the planted store must be refused by name; it met {type(later).__name__}"
        )
    finally:
        again.handle.close()


def test_1_1_a_close_that_raises_while_a_refused_boot_cleans_up_leaves_no_marker(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G-2AB-CLOSE-ORDER: the read refuses the plant and ``close()`` raises; the marker is removed all the same.

    Measured on ``fe25536c`` (``p_b3_close_raises.py``): the boot raised the
    close's ``OSError``, the marker stayed, the retry was ``"verified"`` and a
    governed call over it was answered.
    """
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    manifest, registry, records = p4e._deployment(tmp_path)
    used = p4e._used_question_store(tmp_path, manifest, registry, records)
    target = tmp_path / "plain" / _STORE
    target.parent.mkdir()
    real_boot = manifest_module.boot
    raised_at_close: list[str] = []

    def plant_then_boot_with_a_close_that_raises(**kwargs: Any) -> Any:
        first = not raised_at_close
        if first:
            shutil.copy(used, target)
        handle = real_boot(**kwargs)
        if first:
            real_close = handle.close

            def close_then_raise() -> None:
                real_close()
                raised_at_close.append("raised")
                raise OSError("an error surfacing at close")

            handle.close = close_then_raise
        return handle

    monkeypatch.setattr(manifest_module, "boot", plant_then_boot_with_a_close_that_raises)
    outcome = tp._boot_plainly(manifest, registry, target)
    monkeypatch.setattr(manifest_module, "boot", real_boot)
    assert raised_at_close == ["raised"], (
        f"close() was not called and made to raise; the case was not constructed: {outcome!r}"
    )
    assert isinstance(outcome, Exception), "the planted store must not boot"
    assert p4e._sdk_markers(target) == [], (
        "a refused boot whose close() raised left the marker it created beside the planted store:"
        f" {[marker.name for marker in p4e._sdk_markers(target)]} (it raised {outcome!r})"
    )
    again = tp._boot_plainly(manifest, registry, target)
    assert not isinstance(again, Exception), f"the retry must boot the unmarked store: {again!r}"
    try:
        assert again.store_creation == "unmarked", f"the retry vouched for the plant: {again.store_creation!r}"
        later = tp._later_governed_call(again, registry, records)
        assert m._named(later, "UnmarkedStoreNotPresumedFresh"), f"the retry's governed call met {type(later).__name__}"
    finally:
        again.handle.close()


def test_1_1_the_read_s_refusal_reaches_the_caller_when_close_raises_while_cleaning_up(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal the read raised is what the caller meets; the close's error rides along as a note.

    A design choice of this repair, stated so a later change is visible: the
    close's failure does not replace the refusal that explains why the boot was
    refused (measured on ``fe25536c``: the caller met only the close's
    ``OSError``).
    """
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    manifest, registry, records = p4e._deployment(tmp_path)
    used = p4e._used_question_store(tmp_path, manifest, registry, records)
    target = tmp_path / "plain" / _STORE
    target.parent.mkdir()
    real_boot = manifest_module.boot

    def plant_then_boot_with_a_close_that_raises(**kwargs: Any) -> Any:
        shutil.copy(used, target)
        handle = real_boot(**kwargs)
        real_close = handle.close

        def close_then_raise() -> None:
            real_close()
            raise OSError("an error surfacing at close")

        handle.close = close_then_raise
        return handle

    monkeypatch.setattr(manifest_module, "boot", plant_then_boot_with_a_close_that_raises)
    outcome = tp._boot_plainly(manifest, registry, target)
    assert m._named(outcome, "DeploymentStoreNotEmpty"), (
        f"the caller must meet the read's refusal, not the close's error: {outcome!r}"
    )
    notes = getattr(outcome, "__notes__", [])
    assert any("an error surfacing at close" in note for note in notes), (
        f"the close's error must ride along on the refusal as a note: {notes}"
    )


# --- 2. only markers this boot owns -----------------------------------------------------------------------------


@pytest.mark.parametrize("how", ["replaced by another file", "rewritten in place"])
def test_1_1_a_failed_boot_removes_only_a_marker_that_is_still_the_one_it_created(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, how: str
) -> None:
    """A marker that stopped being this boot's own during the boot is left where it is when the boot fails.

    Inside the boot the marker this boot created is replaced (a new file at the
    path) or rewritten in place (the same file, another owner's text), and a
    used store is planted, so the boot's read refuses. Measured on
    ``fe25536c``: the refused boot unlinked whatever was at the marker's path.
    """
    manifest, registry, records = p4e._deployment(tmp_path)
    used = p4e._used_question_store(tmp_path, manifest, registry, records)
    target = tmp_path / "plain" / _STORE
    target.parent.mkdir()
    someone_elses = b"a marker this boot did not write\n"

    def take_the_marker_over(planted_at: pathlib.Path) -> None:
        marker = _marker(planted_at)
        assert marker.exists(), "the boot left no marker before boot(); the case was not constructed"
        if how == "replaced by another file":
            marker.unlink()
            marker.write_bytes(someone_elses)
        else:
            with open(marker, "r+b") as rewritten:
                rewritten.truncate(0)
                rewritten.write(someone_elses)

    planted = _plant_inside_the_boot(monkeypatch, used, then=take_the_marker_over)
    outcome = tp._boot_plainly(manifest, registry, target)
    assert planted == [_STORE], "the store was not planted; the case was not constructed"
    if not isinstance(outcome, Exception):
        outcome.handle.close()
        pytest.fail(f"[{how}] the planted store must not boot")
    marker = _marker(target)
    assert marker.exists() and marker.read_bytes() == someone_elses, (
        f"[{how}] the failed boot removed or changed a marker that was no longer the one it created"
    )


# --- 3. crash-safe: a marker reads `verified` only after the read completed ----------------------------------------


def test_1_1_a_marker_reads_pending_until_the_read_completes_and_verified_after(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two-phase: inside the boot (before its read) the marker reads ``pending``; once the boot returns, ``verified``."""
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "fresh" / _STORE
    target.parent.mkdir()
    real_boot = manifest_module.boot
    seen: list[str | None] = []

    def boot_and_look(**kwargs: Any) -> Any:
        handle = real_boot(**kwargs)
        seen.append(_state(_marker(target)) if _marker(target).exists() else "no marker")
        return handle

    monkeypatch.setattr(manifest_module, "boot", boot_and_look)
    fabric = load_and_boot(manifest, registry=registry, connection={"database_path": str(target)})
    try:
        after = _state(_marker(target))
        creation = fabric.store_creation
    finally:
        fabric.handle.close()
    assert seen == ["pending"], f"before the boot's read completed, the marker must read pending: {seen}"
    assert after == "verified", f"after the read completed, the marker must read verified: {after!r}"
    assert creation == "verified", creation


def _boot_in_another_process(mode: str, manifest: pathlib.Path, signals: pathlib.Path, store: pathlib.Path) -> subprocess.CompletedProcess[str]:
    root = pathlib.Path(__file__).resolve().parents[2]
    estate = ("PG", "FLUREE_", "MONGO_", "NEO4J_", "CO_LENDER_")
    environment = {key: value for key, value in os.environ.items() if not key.startswith(estate)}
    environment["PYTHONPATH"] = os.pathsep.join(str(root / part) for part in ("src", "runtime"))
    return subprocess.run(
        [sys.executable, "-B", "-m", "tests.products._plain_boot_from_another_process", mode,
         str(manifest), str(signals), str(store)],
        cwd=root, env=environment, capture_output=True, text=True, timeout=300, check=False,
    )


def _assert_refused_unresolved(outcome: Any, *, marker: pathlib.Path, reason: str, case: str) -> None:
    if not isinstance(outcome, Exception):
        held = p4e._held(outcome)
        creation = outcome.store_creation
        outcome.handle.close()
        pytest.fail(
            f"[{case}] a boot over a marker that shows no completed verification booted (store_creation"
            f" {creation!r}, {held} entities held); it must be refused by name ({UNRESOLVED}, reason {reason!r})"
        )
    assert m._named(outcome, UNRESOLVED), f"[{case}] refused, but not by {UNRESOLVED}: {outcome!r}"
    assert getattr(outcome, "reason", None) == reason, f"[{case}] refused for another reason: {outcome.reason!r}"
    assert getattr(outcome, "marker", None) == marker, f"[{case}] the refusal names another marker: {outcome.marker!r}"
    assert str(marker) in str(outcome), f"[{case}] the refusal's text must name the marker's path: {outcome}"
    assert "operator" in str(outcome), f"[{case}] the refusal's text must say an operator resolves it: {outcome}"


@pytest.mark.parametrize("killed", ["crash-before-boot", "crash-after-boot", "crash-during-read"])
def test_1_1_a_boot_killed_before_its_read_completes_leaves_a_marker_no_later_boot_reads_as_verified(
    tmp_path: pathlib.Path, killed: str
) -> None:
    """A plain boot SIGKILLed after its marker and before its read completes; every later boot is refused by name.

    ``crash-before-boot``: killed before the adapter opens the store (none is
    created). ``crash-after-boot``: killed after the adapter created and opened
    the store, before the read. ``crash-during-read``: killed inside the read
    itself, the latest instant before it completes (added after the fix commit;
    its red is measured against ``fe25536c``'s ``manifest.py``). Measured on
    ``fe25536c``: the marker the killed boot left was read as ``"verified"`` by
    the next boot, which booted.
    """
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "crashed" / _STORE
    target.parent.mkdir()
    signals = tmp_path / "signals"
    signals.mkdir()
    ran = _boot_in_another_process(killed, manifest, signals, target)
    assert ran.returncode == -signal.SIGKILL, (
        f"[{killed}] the boot in the other process was not killed as constructed: rc {ran.returncode}"
        f" {ran.stdout[-500:]} {ran.stderr[-2000:]}"
    )
    marker = _marker(target)
    assert marker.exists(), f"[{killed}] the killed boot left no marker; the case was not constructed"
    assert target.exists() == (killed != "crash-before-boot"), f"[{killed}] the store's presence is not as constructed"
    left = marker.read_bytes()
    for read_only in (False, True):
        try:
            outcome: Any = load_and_boot(
                manifest, registry=registry, connection={"database_path": str(target)}, read_only=read_only
            )
        except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
            outcome = raised
        _assert_refused_unresolved(outcome, marker=marker, reason="pending", case=f"{killed}, read_only={read_only}")
    assert marker.read_bytes() == left, f"[{killed}] the refused boots changed the marker; it is the operator's to resolve"
    assert _state(marker) == "pending", (
        f"[{killed}] the marker a boot killed before its read completed must read pending: {left!r}"
    )
    assert target.exists() == (killed != "crash-before-boot"), f"[{killed}] a refused boot created or removed the store"


# --- 4. a marker that cannot show a completed verification ---------------------------------------------------------


@pytest.mark.parametrize("marker_is", ["the single-line marker of fe25536c", "text that is not the SDK's", "a symbolic link"])
def test_1_1_a_marker_whose_state_cannot_be_read_is_refused_by_name_and_left_for_an_operator(
    tmp_path: pathlib.Path, marker_is: str
) -> None:
    """A store with a marker that records no completed verification: every boot of it is refused, the marker untouched.

    The store is the deployment's own, created and written through a door; its
    marker is then made into what this tree wrote before the repair (one line,
    no state), text that is not the SDK's, or a symbolic link to a marker that
    reads ``verified``. Measured on ``fe25536c``: each was booted ``"verified"``,
    reading nothing.
    """
    manifest, registry, records = p4e._deployment(tmp_path)
    target = tmp_path / "kept" / _STORE
    target.parent.mkdir()
    created = load_and_boot(manifest, registry=registry, connection={"database_path": str(target)})
    try:
        for envelope in m._base_accounts():
            created.handle.worker.ingest(envelope)
    finally:
        created.handle.close()
    marker = _marker(target)
    assert marker.exists(), "the deployment's own store carries no marker; the case was not constructed"
    if marker_is == "a symbolic link":
        elsewhere = tmp_path / "elsewhere.ccf-deployment-store"
        shutil.copy(marker, elsewhere)
        marker.unlink()
        marker.symlink_to(elsewhere)
    else:
        marker.write_text(
            _SINGLE_LINE_MARKER if marker_is == "the single-line marker of fe25536c" else "booted, trust me\n",
            encoding="utf-8",
        )
    left = os.readlink(marker) if marker.is_symlink() else marker.read_bytes()
    for read_only in (False, True):
        try:
            outcome: Any = load_and_boot(
                manifest, registry=registry, connection={"database_path": str(target)}, read_only=read_only
            )
        except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
            outcome = raised
        _assert_refused_unresolved(outcome, marker=marker, reason="unreadable", case=f"{marker_is}, read_only={read_only}")
    now = os.readlink(marker) if marker.is_symlink() else marker.read_bytes()
    assert now == left, f"[{marker_is}] the refused boots changed the marker; it is the operator's to resolve"


def test_1_1_control_a_boot_that_verifies_an_empty_new_store_boots_and_a_reopen_takes_no_read(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control (green before and after): created empty and read once, it boots verified; reopened, it is not read."""
    manifest, registry, records = p4e._deployment(tmp_path)
    events: list[tuple[str, ...]] = []
    p4e._record_reads(monkeypatch, events)
    target = tmp_path / "fresh" / _STORE
    target.parent.mkdir()
    created = load_and_boot(manifest, registry=registry, connection={"database_path": str(target)})
    reads_creating = tp._latest_reads(events)
    try:
        assert created.store_creation == "verified", created.store_creation
        for envelope in m._base_accounts():
            created.handle.worker.ingest(envelope)
    finally:
        created.handle.close()
    events.clear()
    reopened = load_and_boot(manifest, registry=registry, connection={"database_path": str(target)})
    try:
        reads_reopening = tp._latest_reads(events)
        assert reopened.store_creation == "verified", reopened.store_creation
        answered = tp._later_governed_call(reopened, registry, records)
    finally:
        reopened.handle.close()
    assert reads_creating == 1 and reads_reopening == 0, (reads_creating, reads_reopening)
    assert type(answered).__name__ == "ServedProduct", f"the deployment's own store, reopened, must answer: {answered!r}"


def test_1_1_the_helper_process_measures_this_tree(tmp_path: pathlib.Path) -> None:
    """The cross-process helper imports THIS tree's ``ccf`` (a measurement of another tree would be no measurement)."""
    manifest, _registry, _records = p4e._deployment(tmp_path)
    signals = tmp_path / "signals"
    signals.mkdir()
    store = tmp_path / "helper" / _STORE
    store.parent.mkdir()
    ran = _boot_in_another_process("boot", manifest, signals, store)
    assert ran.returncode == 0, ran.stderr[-2000:]
    report = json.loads(ran.stdout.strip().splitlines()[-1])
    root = pathlib.Path(__file__).resolve().parents[2]
    assert pathlib.Path(report["imported"]).is_relative_to(root / "src"), report["imported"]
    assert report["outcome"] == "booted" and report["created_the_store"] is True, report
