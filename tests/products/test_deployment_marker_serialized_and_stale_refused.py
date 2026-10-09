"""SEC-020, D-IMPL-378 repair 1.2: every plain boot that creates a store reads it; creation is serialized; stale is refused.

Dave, 2026-10-09 10:54 MST, verbatim: *"Run the emptiness check whenever a plain
boot creates a new store. Serialize creation and verification; test competing
boots. If safe verification cannot be established, refuse until an operator
resolves the stale marker."* It restores the trigger of OWED-RULINGS-3 item 2A
(b) as ruled at 06:21 MST (*"Run the same one emptiness read when a plain boot
creates a new store"*), which the build had narrowed to "a plain boot that
created its deployment marker in this boot" (the panel's G-2AB-TRIGGER). SEC-020
stays OPEN: these tests measure what the SDK refuses, and nothing here closes
it.

What was measured before the repair, on ``dl-378-integ`` @ ``fe25536c`` (lane
``378i-small``'s ``probe_stale_deployment_marker.py`` and lane ``378j-boot``'s
``probe_race.py``, re-run): a path that kept its deployment marker after its
store was deleted was booted again with no read, a used store planted inside
that boot was booted ``"verified"``, and a governed call over it was answered.
Two plain boots racing on one fresh path, in two processes, 40 trials: in 28
the boot whose adapter created the store returned ``"verified"`` having read
nothing (the read went to the boot that made the marker, whichever that was);
with one of the two boots read-only, 15 of 40.

What is asserted, by mechanism:

1. **Where safe verification cannot be established, refused by name and left
   for an operator.** A store-creation lock that cannot be taken
   (``lock-unavailable``) and a marker that appeared at the path after the boot
   looked (``claimed``) are each refused (``DeploymentStoreNotVerified``) before
   any store is created there, and nothing beside the path is cleared.
1b. **A stale marker with no store beside it is replaced and verified afresh**
   (built as the lane's proposal P-1 (B), the no-store case only). Under the
   store-creation lock no live boot owns a marker the boot finds, so a marker of
   any state (``pending``, ``verified``, or not in the SDK's form) with no store
   beside it is replaced by the boot's own, which takes the one read a fresh
   creation takes: a store planted before the store opens is refused
   (``DeploymentStoreNotEmpty``), and of two racing boots one creates and
   verifies while the other waits and reopens. Until this, such a boot was
   refused (``no-store``, ``pending`` or ``unreadable``) until an operator
   removed the marker.
2. **The read runs whenever a plain boot creates a store**, whoever made the
   marker beside the path: a store created at a path a question marker had
   reserved is read, and a plant there is refused (``DeploymentStoreNotEmpty``).
3. **Creation and verification are serialized**, across processes. A boot that
   finds another boot creating the store waits until that boot has verified it
   and then reopens it, reading nothing; two boots racing on a fresh path never
   both create it, the one that creates it reads it once, the other never
   serves a store it did not verify and is never refused as stale.

Refusals are asserted by their class NAME and their ``reason``, so a tree
without the repair fails each test on its behavior, never on an import. Every
domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time
from typing import Any

import pytest

from ccf.deployment import load_and_boot
from tests.products import test_plain_boot_creating_its_store_finds_it_empty as tp
from tests.products import test_question_store_empty_at_boot_and_held_through_use as p4e
from tests.products import test_withheld_subject_population_composite_and_fabric as m

#: The refusal a boot meets where safe verification cannot be established (absent on a tree without it).
NOT_VERIFIED = "DeploymentStoreNotVerified"

#: The store file every hand-composed fixture fabric here names.
_STORE = "graph.sqlite3"

#: What a plain boot appends to the resolved store path to name its marker (fragment 378-34).
_DEPLOYMENT_MARKER_SUFFIX = ".ccf-deployment-store"

#: What a plain boot appends to the resolved store path to name the lock it serializes creation under.
_STORE_CREATION_LOCK_SUFFIX = ".ccf-store-creation.lock"

#: How long a boot that must wait is watched before the test concludes it is waiting (a test-side bound).
_WATCH_SECONDS = 3.0


def _marker(store: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(f"{store.resolve()}{_DEPLOYMENT_MARKER_SUFFIX}")


def _state(marker: pathlib.Path) -> str | None:
    for line in marker.read_text(encoding="utf-8").splitlines():
        if line.startswith("state: "):
            return line.removeprefix("state: ")
    return None


def _boot(manifest: pathlib.Path, registry: Any, store: pathlib.Path, *, read_only: bool = False) -> Any:
    try:
        return load_and_boot(manifest, registry=registry, connection={"database_path": str(store)}, read_only=read_only)
    except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
        return raised


def _assert_refused_not_verified(outcome: Any, *, marker: pathlib.Path, reason: str, case: str) -> None:
    if not isinstance(outcome, Exception):
        creation, held = outcome.store_creation, p4e._held(outcome)
        outcome.handle.close()
        pytest.fail(
            f"[{case}] a boot where safe verification cannot be established booted (store_creation {creation!r},"
            f" {held} entities held); it must be refused by name ({NOT_VERIFIED}, reason {reason!r})"
        )
    assert m._named(outcome, NOT_VERIFIED), f"[{case}] refused, but not by {NOT_VERIFIED}: {outcome!r}"
    assert getattr(outcome, "reason", None) == reason, f"[{case}] refused for another reason: {outcome.reason!r}"
    assert getattr(outcome, "marker", None) == marker, f"[{case}] the refusal names another marker: {outcome.marker!r}"
    assert str(marker) in str(outcome), f"[{case}] the refusal's text must name the marker's path: {outcome}"
    assert "operator" in str(outcome), f"[{case}] the refusal's text must say an operator resolves it: {outcome}"


def _planting(monkeypatch: pytest.MonkeyPatch, used: pathlib.Path) -> list[str]:
    """Write a used store at the boot's path inside its next boot call, after every check it made there."""
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    real_boot = manifest_module.boot
    planted: list[str] = []

    def plant_then_boot(**kwargs: Any) -> Any:
        if not planted:
            target = pathlib.Path(str(kwargs["connection"]["database_path"]))
            shutil.copy(used, target)
            planted.append(target.name)
        return real_boot(**kwargs)

    monkeypatch.setattr(manifest_module, "boot", plant_then_boot)
    return planted


# --- 1. where safe verification cannot be established: refused by name, nothing cleared -------------------------


def test_1_2_a_store_creation_lock_that_cannot_be_taken_refuses_the_boot_by_name(tmp_path: pathlib.Path) -> None:
    """The serialization lock unavailable (here a directory stands at its path): refused by name, nothing created."""
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "plain" / _STORE
    target.parent.mkdir()
    lock = pathlib.Path(f"{target.resolve()}{_STORE_CREATION_LOCK_SUFFIX}")
    lock.mkdir()
    outcome = _boot(manifest, registry, target)
    _assert_refused_not_verified(outcome, marker=_marker(target), reason="lock-unavailable", case="lock is a directory")
    assert str(lock) in str(outcome), f"the refusal's text must name the lock's path: {outcome}"
    assert not target.exists() and not _marker(target).exists(), "a refused boot created a store or a marker"
    assert lock.is_dir(), "the refused boot changed what stands at the lock's path"


def test_1_2_a_marker_that_appears_after_the_boot_looked_is_refused_as_claimed(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A writer outside the SDK makes the marker between the boot's look and its exclusive create: refused, not booted.

    Measured on ``de9b28f`` (repair 1.1, before 1.2): the boot took the other
    writer's marker as a concurrent boot's, booted the store it created with no
    read, and handed the fabric back.
    """
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "plain" / _STORE
    target.parent.mkdir()
    foreign = b"a marker a writer outside the SDK made\n"
    real_create = manifest_module._create_pending_deployment_marker

    def an_outside_writer_first(path: pathlib.Path) -> Any:
        _marker(path).write_bytes(foreign)
        return real_create(path)

    monkeypatch.setattr(manifest_module, "_create_pending_deployment_marker", an_outside_writer_first)
    outcome = _boot(manifest, registry, target)
    _assert_refused_not_verified(outcome, marker=_marker(target), reason="claimed", case="a marker made after the look")
    assert not target.exists(), "a refused boot created a store at the path"
    assert _marker(target).read_bytes() == foreign, "the refused boot changed a marker it did not create"


def test_1_2_measure_a_marker_replaced_before_promotion_is_refused_as_claimed_and_left(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A measurement of repair 1.1's promotion (passes from ``de9b28f`` on): a marker no longer this boot's is not made verified.

    Inside the boot the marker this boot created is replaced by another file;
    the store is fresh, so the read passes, and the promotion meets a marker
    that is not its own.
    """
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "plain" / _STORE
    target.parent.mkdir()
    real_boot = manifest_module.boot
    foreign = b"a marker this boot did not write\n"

    def replace_the_marker_then_boot(**kwargs: Any) -> Any:
        _marker(target).unlink()
        _marker(target).write_bytes(foreign)
        return real_boot(**kwargs)

    monkeypatch.setattr(manifest_module, "boot", replace_the_marker_then_boot)
    outcome = _boot(manifest, registry, target)
    _assert_refused_not_verified(outcome, marker=_marker(target), reason="claimed", case="replaced before promotion")
    assert _marker(target).read_bytes() == foreign, "the refused boot removed or changed a marker it did not own"


# --- 1b. a stale marker with no store beside it: replaced under the lock, and the new store read -------------------

#: The first line of every deployment marker the SDK writes (fragment 378-34), and the whole of one written before
#: repair 1.1.
_MARKER_HEAD = "created by a boot not for a question; no acquisition phase writes into it (SEC-020, D-IMPL-378)\n"

#: A boot token no boot of these tests wrote: a stale marker's, written as text.
_FOREIGN_TOKEN = "0123456789abcdef0123456789abcdef"

#: The states a deployment marker can be left in with no store beside it.
STALE_WITH_NO_STORE = (
    "pending, left by a boot killed before its store existed",
    "verified, its store deleted",
    "the single-line marker of fe25536c",
    "text that is not the SDK's",
    "a symbolic link",
)


def _token(marker: pathlib.Path) -> str | None:
    """The ``boot:`` token a deployment marker records, or ``None`` when it records none."""
    for line in marker.read_text(encoding="utf-8").splitlines():
        if line.startswith("boot: "):
            return line.removeprefix("boot: ")
    return None


def _stale_with_no_store(tmp_path: pathlib.Path, manifest: pathlib.Path, registry: Any, target: pathlib.Path, state: str) -> None:
    """Leave a deployment marker in ``state`` beside ``target``, and no store there."""
    marker = _marker(target)
    if state == "pending, left by a boot killed before its store existed":
        signals = tmp_path / f"signals-{target.parent.name}"
        signals.mkdir()
        killed = _another_process("crash-before-boot", str(manifest), str(signals), str(target))
        _out, err = killed.communicate(timeout=300)
        assert killed.returncode == -signal.SIGKILL, (
            f"the boot was not killed as constructed: rc {killed.returncode} {err[-2000:]}"
        )
    elif state == "verified, its store deleted":
        load_and_boot(manifest, registry=registry, connection={"database_path": str(target)}).handle.close()
        for suffix in ("", "-wal", "-shm"):
            pathlib.Path(f"{target}{suffix}").unlink(missing_ok=True)
    elif state == "the single-line marker of fe25536c":
        marker.write_text(_MARKER_HEAD, encoding="utf-8")
    elif state == "text that is not the SDK's":
        marker.write_text("booted, trust me\n", encoding="utf-8")
    else:
        elsewhere = tmp_path / f"elsewhere-{target.parent.name}.ccf-deployment-store"
        elsewhere.write_text(f"{_MARKER_HEAD}state: verified\nboot: {_FOREIGN_TOKEN}\n", encoding="utf-8")
        marker.symlink_to(elsewhere)
    assert os.path.lexists(marker) and not target.exists(), f"[{state}] the stale marker with no store was not constructed"
    if state.startswith(("pending", "verified")):
        assert _state(marker) == state.split(",")[0], f"[{state}] the marker reads {_state(marker)!r}"


@pytest.mark.parametrize("state", STALE_WITH_NO_STORE)
def test_1_2_b_a_stale_marker_with_no_store_beside_it_is_replaced_and_the_new_store_read_once_and_verified(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """A deployment marker of any state with no store beside it: the boot creates a new store, so it verifies it afresh.

    Repair 1.2 (*"Run the emptiness check whenever a plain boot creates a new
    store"*), built as the lane's proposal P-1 (B) for this case only: under the
    store-creation lock no live boot owns a marker it finds, so the boot
    replaces the stale marker with its own, reading ``pending``, takes the one
    read a fresh creation takes, and marks it ``verified``. Measured on
    ``3119297a`` (where each was refused until an operator removed the marker:
    ``pending``, ``no-store`` or ``unreadable``) and on ``fe25536c`` (where the
    verified one was booted with no read, the small lane's P-B).
    """
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "stale" / _STORE
    target.parent.mkdir()
    _stale_with_no_store(tmp_path, manifest, registry, target, state)
    marker = _marker(target)
    linked = marker.resolve() if marker.is_symlink() else None
    linked_bytes = linked.read_bytes() if linked is not None else None
    stale_token = None if linked is not None else _token(marker)
    events: list[tuple[str, ...]] = []
    p4e._record_reads(monkeypatch, events)
    outcome = _boot(manifest, registry, target)
    if isinstance(outcome, Exception):
        pytest.fail(
            f"[{state}] a boot at a path with a stale marker and no store was refused ({outcome!r}); with no store"
            " beside the marker the boot creates a new store, which it can verify as any fresh creation"
        )
    try:
        reads = tp._latest_reads(events)
        creation, held = outcome.store_creation, p4e._held(outcome)
    finally:
        outcome.handle.close()
    assert reads == 1, f"[{state}] the boot that created the store must read it exactly once: {reads}"
    assert creation == "verified" and held == 0, f"[{state}] store_creation {creation!r}, {held} entities held"
    assert not marker.is_symlink() and _state(marker) == "verified", f"[{state}] the marker must now be this boot's, verified"
    assert _token(marker) not in (None, stale_token), f"[{state}] the stale marker was not replaced by this boot's own"
    if linked is not None:
        assert linked.read_bytes() == linked_bytes, f"[{state}] the file the stale link named was changed"


@pytest.mark.parametrize(
    "state",
    ["pending, left by a boot killed before its store existed", "verified, its store deleted", "the single-line marker of fe25536c"],
)
def test_1_2_b_a_store_planted_after_the_look_beside_a_stale_marker_is_refused_by_the_read_and_the_marker_removed(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """The re-verified path is as safe as a fresh one: a used store planted after the look is refused by the read.

    The plant lands inside the boot, after the stale marker was replaced and
    before the adapter opens the store. The boot's read refuses it
    (``DeploymentStoreNotEmpty``) and removes the marker it put there, so the
    path is left holding the plant with no marker beside it: a later boot opens
    it ``"unmarked"`` and a governed call over it is refused. Measured on
    ``3119297a``: refused at the look, before any read (the plant never
    happened); on ``fe25536c`` (verified marker): booted ``"verified"`` with no
    read and answered (``probe_stale_deployment_marker.py``).
    """
    manifest, registry, records = p4e._deployment(tmp_path)
    used = p4e._used_question_store(tmp_path, manifest, registry, records)
    target = tmp_path / "stale" / _STORE
    target.parent.mkdir()
    _stale_with_no_store(tmp_path, manifest, registry, target, state)
    planted = _planting(monkeypatch, used)
    outcome = _boot(manifest, registry, target)
    if not m._named(outcome, "DeploymentStoreNotEmpty"):
        what = repr(outcome)
        if not isinstance(outcome, Exception):
            what = f"it booted (store_creation {outcome.store_creation!r}, {p4e._held(outcome)} entities held)"
            outcome.handle.close()
        pytest.fail(f"[{state}] a store planted after the look must be refused by the boot's read: {what}")
    assert planted == [_STORE], f"[{state}] the store was not planted; the case was not constructed: {planted}"
    assert p4e._sdk_markers(target) == [], (
        f"[{state}] the refused boot must leave no marker beside the plant: {[p.name for p in p4e._sdk_markers(target)]}"
    )
    again = _boot(manifest, registry, target)
    assert not isinstance(again, Exception), f"[{state}] the retry must boot the unmarked store: {again!r}"
    try:
        assert again.store_creation == "unmarked", f"[{state}] the retry vouched for the plant: {again.store_creation!r}"
        later = tp._later_governed_call(again, registry, records)
        assert m._named(later, "UnmarkedStoreNotPresumedFresh"), f"[{state}] the retry's governed call met {type(later).__name__}"
    finally:
        again.handle.close()


@pytest.mark.parametrize("roles", [("writer", "writer"), ("writer", "read-only")])
def test_1_2_b_two_plain_boots_racing_on_stale_no_store_paths_never_serve_a_store_they_did_not_verify(
    tmp_path: pathlib.Path, roles: tuple[str, str]
) -> None:
    """Free-running, two processes, twelve trials: each path holds a stale marker (four states in turn) and no store.

    Per trial: exactly one boot's adapter created the store; that boot read it
    once and booted ``"verified"``; the other read nothing, did not create it,
    and either reopened it ``"verified"`` or, as a second writer while the
    first still held the store, was refused ``SingleWriterViolation``; neither
    was refused as stale; the stale marker was replaced, and reads
    ``verified``. Measured on ``3119297a``: every boot was refused at the look.
    """
    trials = 12
    stale_texts = (
        f"{_MARKER_HEAD}state: pending\nboot: {_FOREIGN_TOKEN}\n",
        f"{_MARKER_HEAD}state: verified\nboot: {_FOREIGN_TOKEN}\n",
        _MARKER_HEAD,
        "booted, trust me\n",
    )
    manifest, _registry, _records = p4e._deployment(tmp_path)
    signals, stores = tmp_path / "signals", tmp_path / "stores"
    signals.mkdir()
    stores.mkdir()
    for trial in range(trials):
        target = stores / str(trial) / _STORE
        target.parent.mkdir()
        _marker(target).write_text(stale_texts[trial % len(stale_texts)], encoding="utf-8")
    racing = [
        _another_process("race", str(manifest), str(signals), str(stores), str(role_id), role, str(trials))
        for role_id, role in enumerate(roles)
    ]
    reports = [_report(process, timeout=600) for process in racing]
    for trial in range(trials):
        pair = [report["trials"][trial] for report in reports]
        assert all(each.get("outcome") in ("booted", "raised") for each in pair), pair
        created = [each for each in pair if each["created_the_store"]]
        assert len(created) == 1, f"[trial {trial}] exactly one boot must create the store: {pair}"
        creator = created[0]
        other = pair[1 - pair.index(creator)]
        assert creator["outcome"] == "booted" and creator["store_creation"] == "verified", f"[trial {trial}] {creator}"
        assert creator["emptiness_reads"] == 1, f"[trial {trial}] the boot that created the store must read it once: {creator}"
        assert other["emptiness_reads"] == 0, f"[trial {trial}] the boot that did not create the store must not read: {other}"
        if other["outcome"] == "booted":
            assert other["store_creation"] == "verified", f"[trial {trial}] {other}"
        else:
            assert other["raised"][0] == "SingleWriterViolation", (
                f"[trial {trial}] the other boot may only be refused as a second writer, never as stale: {other}"
            )
        marker = _marker(stores / str(trial) / _STORE)
        assert _state(marker) == "verified" and _token(marker) not in (None, _FOREIGN_TOKEN), (
            f"[trial {trial}] the stale marker must be replaced by the creating boot's own, verified"
        )


# --- 2. the read runs whenever a plain boot creates a store ---------------------------------------------------------


def test_1_2_a_plain_boot_creating_a_store_where_a_question_marker_stands_takes_the_read(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whoever made the marker: a store created at a path a question boot reserved (and failed on) is read, the plant refused.

    A boot for a question reserves the path and fails inside ``boot()`` before
    its store exists, so its question marker stands with no store beside it
    (that marker stays: the question path's behavior). A plain boot of the path
    then creates the store, with a used store planted inside the boot. Measured
    on ``de9b28f``: no read was taken, because this boot made no marker; the
    plant was booted (a reopened question's store, refused only later, at a
    governed call).
    """
    import ccf.deployment.manifest as manifest_module  # noqa: PLC0415

    manifest, registry, records = p4e._deployment(tmp_path)
    used = p4e._used_question_store(tmp_path, manifest, registry, records)
    target = tmp_path / "reserved" / _STORE
    target.parent.mkdir()

    def fail_inside_the_question_boot(**kwargs: Any) -> Any:
        raise RuntimeError("the question boot fails inside boot(), before its store exists")

    monkeypatch.setattr(manifest_module, "boot", fail_inside_the_question_boot)
    with pytest.raises(RuntimeError):
        load_and_boot(manifest, registry=registry, connection={"database_path": str(target)}, for_question=True)
    question_marker = pathlib.Path(f"{target.resolve()}.ccf-question-store")
    assert question_marker.exists() and not target.exists(), "the reserved path was not constructed"
    monkeypatch.undo()
    planted = _planting(monkeypatch, used)
    outcome = _boot(manifest, registry, target)
    assert planted == [_STORE], "the store was not planted; the case was not constructed"
    if not m._named(outcome, "DeploymentStoreNotEmpty"):
        what = repr(outcome)
        if not isinstance(outcome, Exception):
            what = f"it booted (store_creation {outcome.store_creation!r}, {p4e._held(outcome)} entities held)"
            outcome.handle.close()
        pytest.fail(f"a plain boot that created the store at a question's reserved path took no read: {what}")
    assert not _marker(target).exists(), "the refused boot left a deployment marker beside the plant"
    later = _boot(manifest, registry, target)
    assert not isinstance(later, Exception), f"reopening must boot: {later!r}"
    try:
        answered = tp._later_governed_call(later, registry, records)
    finally:
        later.handle.close()
    assert type(answered).__name__ in ("QuestionStoreReopened", "UnmarkedStoreNotPresumedFresh"), (
        f"a governed call over the plant must be refused by name: it met {type(answered).__name__}"
    )


# --- 3. creation and verification serialized, across processes ------------------------------------------------------


def _another_process(*arguments: str) -> subprocess.Popen[str]:
    root = pathlib.Path(__file__).resolve().parents[2]
    estate = ("PG", "FLUREE_", "MONGO_", "NEO4J_", "CO_LENDER_")
    environment = {key: value for key, value in os.environ.items() if not key.startswith(estate)}
    environment["PYTHONPATH"] = os.pathsep.join(str(root / part) for part in ("src", "runtime"))
    return subprocess.Popen(
        [sys.executable, "-B", "-m", "tests.products._plain_boot_from_another_process", *arguments],
        cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def _report(process: subprocess.Popen[str], *, timeout: float = 300) -> dict[str, Any]:
    out, err = process.communicate(timeout=timeout)
    assert process.returncode == 0, f"the other process failed: rc {process.returncode} {err[-3000:]}"
    report: dict[str, Any] = json.loads(out.strip().splitlines()[-1])
    root = pathlib.Path(__file__).resolve().parents[2]
    assert pathlib.Path(report["imported"]).is_relative_to(root / "src"), f"another tree was measured: {report['imported']}"
    return report


def _wait_for(path: pathlib.Path, *, process: subprocess.Popen[str], seconds: float = 60) -> None:
    deadline = time.monotonic() + seconds
    while not path.exists():
        if process.poll() is not None:
            out, err = process.communicate()
            pytest.fail(f"the other process ended before {path.name}: rc {process.returncode} {out[-1000:]} {err[-2000:]}")
        if time.monotonic() > deadline:
            process.kill()
            pytest.fail(f"the other process never reached {path.name}")
        time.sleep(0.01)


def test_1_2_a_boot_that_meets_another_boot_creating_the_store_waits_for_its_verification_then_reopens(
    tmp_path: pathlib.Path,
) -> None:
    """Two processes, deterministic: A is held inside its boot after its marker; B (read-only) waits, then reopens.

    A (a writer) creates its marker and stops inside ``boot()``, before the
    adapter opens the store, until released. B starts while A is stopped. With
    creation and verification serialized, B cannot finish while A is stopped;
    once A is released and has verified the store, B opens the store A
    created, reading nothing. Measured on ``fe25536c``: B finished while A was
    stopped, having created the store itself with no read, ``"verified"``. On
    ``de9b28f``: B finished while A was stopped, refused by name as if A's
    marker were stale.
    """
    manifest, _registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "contended" / _STORE
    target.parent.mkdir()
    signals_a, signals_b = tmp_path / "signals-a", tmp_path / "signals-b"
    signals_a.mkdir()
    signals_b.mkdir()
    first = _another_process("pause-inside-boot", str(manifest), str(signals_a), str(target))
    second: subprocess.Popen[str] | None = None
    try:
        _wait_for(signals_a / "inside", process=first)
        second = _another_process("boot", str(manifest), str(signals_b), str(target), "read-only")
        _wait_for(signals_b / "starting", process=second)
        deadline = time.monotonic() + _WATCH_SECONDS
        while second.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        finished_while_held = second.poll() is not None
    finally:
        (signals_a / "release").write_text("release\n")
    a = _report(first)
    b = _report(second)
    assert a["outcome"] == "booted" and a["created_the_store"] is True and a["emptiness_reads"] == 1, (
        f"the first boot must create the store and read it once: {a}"
    )
    assert a["store_creation"] == "verified", a
    assert not finished_while_held, (
        "a boot that met another boot creating the same store finished while that boot was still inside its"
        f" creation; it must wait for the creation to be verified: {b}"
    )
    assert b["outcome"] == "booted", f"the waiting boot must boot once the store is verified: {b}"
    assert b["created_the_store"] is False and b["emptiness_reads"] == 0, (
        f"the waiting boot must reopen the store the first boot created, reading nothing: {b}"
    )
    assert b["store_creation"] == "verified", b
    assert _state(_marker(target)) == "verified", "the marker must read verified once the creation was verified"


@pytest.mark.parametrize("roles", [("writer", "writer"), ("writer", "read-only")])
def test_1_2_two_plain_boots_racing_on_fresh_paths_in_two_processes_never_serve_a_store_they_did_not_verify(
    tmp_path: pathlib.Path, roles: tuple[str, str]
) -> None:
    """Free-running: two processes meet at a barrier and boot one fresh path, twelve times, each time a new path.

    Per trial: exactly one boot's adapter created the store; that boot read it
    once and booted ``"verified"``; the other read nothing, did not create it,
    and either booted ``"verified"`` (reopened) or, as a second writer while the
    first still held the store, was refused ``SingleWriterViolation``; neither
    was refused as stale; the marker reads ``verified``. Measured on
    ``fe25536c`` (``probe_race.py``, 40 trials): the creating boot booted with
    no read in 28 (writer, writer) and 15 (writer, read-only) trials.
    """
    trials = 12
    manifest, _registry, _records = p4e._deployment(tmp_path)
    signals, stores = tmp_path / "signals", tmp_path / "stores"
    signals.mkdir()
    stores.mkdir()
    racing = [
        _another_process("race", str(manifest), str(signals), str(stores), str(role_id), role, str(trials))
        for role_id, role in enumerate(roles)
    ]
    reports = [_report(process, timeout=600) for process in racing]
    outcomes: list[str] = []
    for trial in range(trials):
        pair = [report["trials"][trial] for report in reports]
        assert all("outcome" in each and each["outcome"] != "barrier-timed-out" for each in pair), pair
        outcomes.append(" + ".join(f"{each['outcome']}:{each.get('store_creation') or each.get('raised', ['?'])[0]}" for each in pair))
        created = [each for each in pair if each["created_the_store"]]
        assert len(created) == 1, f"[trial {trial}] exactly one boot must create the store: {pair}"
        creator = created[0]
        other = pair[1 - pair.index(creator)]
        assert creator["outcome"] == "booted" and creator["store_creation"] == "verified", f"[trial {trial}] {creator}"
        assert creator["emptiness_reads"] == 1, f"[trial {trial}] the boot that created the store must read it once: {creator}"
        assert other["emptiness_reads"] == 0, f"[trial {trial}] the boot that did not create the store must not read: {other}"
        if other["outcome"] == "booted":
            assert other["store_creation"] == "verified", f"[trial {trial}] {other}"
        else:
            assert other["raised"][0] == "SingleWriterViolation", (
                f"[trial {trial}] the other boot may only be refused as a second writer, never as stale: {other}"
            )
        target = stores / str(trial) / _STORE
        assert _state(_marker(target)) == "verified", f"[trial {trial}] the marker must read verified"
    assert len(outcomes) == trials, outcomes


def test_1_2_control_a_read_only_boot_beside_a_live_writer_is_not_held_by_the_store_creation_lock(
    tmp_path: pathlib.Path,
) -> None:
    """Control (green before and after): the lock is held through a boot, never through the fabric's life.

    A writer fabric of the store stays open; a read-only boot of the same store
    (Decision Replay's) boots ``"verified"`` with no read, in another process.
    """
    manifest, registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "live" / _STORE
    target.parent.mkdir()
    writer = load_and_boot(manifest, registry=registry, connection={"database_path": str(target)})
    try:
        signals = tmp_path / "signals"
        signals.mkdir()
        reader = _report(_another_process("boot", str(manifest), str(signals), str(target), "read-only"), timeout=120)
    finally:
        writer.handle.close()
    assert reader["outcome"] == "booted" and reader["store_creation"] == "verified", reader
    assert reader["emptiness_reads"] == 0 and reader["created_the_store"] is False, reader
