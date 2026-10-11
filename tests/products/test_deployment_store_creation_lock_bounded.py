# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-020, D-IMPL-378 decision 19 (b): a store-creation lock another holds refuses the boot by name, at once or after a declared wait.

Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation (recorded on ``main`` @ ``c470416f``), verbatim: *"(b) Wait
a bounded time, then refuse by name. An unbounded wait is not a lock."* The option he ruled, the "j" batch panel's
F-J2-1 option (b): a bounded wait, a deployment setting with no SDK default (``D-IMPL-38``), after which the boot
refuses by name (``DeploymentStoreNotVerified``, with a lock reason naming the lock path), the pinned wait test
amended to a bounded wait. At 17:53 MST (``main`` @ ``5278eb1c``) he answered question 2 with its option (a): where a
deployment sets no bound, *"a boot that finds the store-creation lock held refuses at once, by name, as the writer
lease does"*, and the bound stays an optional deployment setting with no SDK default (*"unset means no wait"*).
SEC-020 stays OPEN: these tests measure what the SDK refuses, and nothing here closes it.

What was measured before, on ``83af5650`` (this lane's base; the panel's probe ``p_lock_held_forever.py``, copied into
the lane and re-run): with another process holding ``<store>.ccf-store-creation.lock``, a plain read-only boot of the
store sat inside ``load_and_boot`` for the whole 4-second watch, refused nothing and created nothing, and booted once
the holder let go. A holder that never lets go (a boot stopped inside its span, a process on a hung volume, any
process that locks the file) wedged every plain boot of the path, writer and read-only alike, with no refusal.

What is asserted, by mechanism:

1. **No wait declared: refused at once, by name.** With the lock held by another holder, a plain boot (writer and
   read-only, in another process) returns while the lock is still held, refused ``DeploymentStoreNotVerified`` with
   reason ``lock-held``, its ``lock`` the lock's path and its text naming that path, before the adapter is reached
   and with nothing created at the path.
2. **A wait declared: the boot waits that long, then is refused by name**, as in 1, while the lock is still held,
   having waited at least the declared seconds.
3. **A wait declared, and the holder lets go within it: the boot proceeds.** It returns only after the release, and
   creates and verifies the store as any boot creating one.
4. **The config door carries the setting.** ``ccf_config.yaml`` declares it, the manifest the door derives carries
   it, and a boot through that door waits and is refused as in 2.
5. **The setting is the deployment's, typed, and the SDK supplies none** (``D-IMPL-38``). Absent, both documents read
   ``None``; a positive whole number of seconds is kept; zero, a negative number, a fraction, a boolean and a quoted
   number are refused at parse; a document declaring none hashes as it did before the field existed.
6. **Competing boots with no wait declared never serve a store they did not verify** (repair 1.2: *"test competing
   boots"*): two processes, twelve trials per pairing. Exactly one boot creates the store and reads it once; the
   other reopens it, or is refused as a second writer or ``lock-held``, never as stale.

Refusals are asserted by their class NAME, their ``reason`` and their ``lock``, so a tree without the setting fails
each test on its behavior or its parse, never on an import. Every domain value here is fixture vocabulary (CINV-01,
CLAUDE.md §11); every wait and watch is a test-side value, never one the SDK supplies.
"""

from __future__ import annotations

import fcntl
import os
import pathlib
import threading
import time
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash, hash_transparent_fields
from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    DEPLOYMENT_MANIFEST,
    ArtifactLoadError,
    DeploymentConfig,
    DeploymentManifest,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.config import derive_deployment, load_config_and_boot
from tests.deployment.conftest import write_artifact
from tests.deployment.test_config_equivalence import _config_document
from tests.products import _deployment_wait_bound as wb
from tests.products import test_deployment_marker_serialized_and_stale_refused as sr
from tests.products import test_question_store_empty_at_boot_and_held_through_use as p4e

#: The refusal a boot meets where the store-creation lock is held by another.
NOT_VERIFIED = "DeploymentStoreNotVerified"

#: How long a boot that must be refused at once is watched before the test concludes it is waiting (test-side).
_AT_ONCE_WATCH_SECONDS = 30.0

#: The wait a deployment declares where the holder never lets go during the boot (test-side, small).
_SHORT_WAIT_SECONDS = 2

#: The wait a deployment declares where the holder lets go first (test-side, far above the watch below).
_LONG_WAIT_SECONDS = 120

#: How long a boot under the long wait is watched, the lock held, before the holder lets go (test-side).
_WAITING_WATCH_SECONDS = 2.0


class _Holder:
    """An exclusive ``flock`` on a lock file, held from this process as another boot or any process can hold it."""

    def __init__(self, lock: pathlib.Path) -> None:
        self._descriptor: int | None = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
        fcntl.flock(self._descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def release(self) -> int:
        """Let go (closing the descriptor drops the lock); the monotonic instant just before, in nanoseconds."""
        released_ns = time.monotonic_ns()
        if self._descriptor is not None:
            os.close(self._descriptor)
            self._descriptor = None
        return released_ns


def _lock(store: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(f"{store.resolve()}{sr._STORE_CREATION_LOCK_SUFFIX}")


def _finishes_within(process: Any, seconds: float) -> bool:
    """Whether ``process`` ends within ``seconds``."""
    deadline = time.monotonic() + seconds
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    return process.poll() is not None


def _assert_refused_lock_held(report: dict[str, Any], *, lock: pathlib.Path, target: pathlib.Path, case: str) -> None:
    """Refused by name, for the held lock, naming it, before the adapter was reached, nothing created at the path."""
    assert report["outcome"] == "raised", f"[{case}] the boot booted while another held the store-creation lock: {report}"
    assert NOT_VERIFIED in report["raised"], (
        f"[{case}] refused, but not by {NOT_VERIFIED}: {report['raised'][0]}: {report.get('message')}"
    )
    assert report["reason"] == "lock-held", f"[{case}] refused for another reason: {report['reason']!r}"
    assert report["lock"] == str(lock), f"[{case}] the refusal names another lock: {report['lock']!r}"
    assert str(lock) in report["message"], f"[{case}] the refusal's text must name the lock's path: {report['message']}"
    assert report["created_the_store"] is None and report["emptiness_reads"] == 0, (
        f"[{case}] the refused boot reached the adapter or read a store: {report}"
    )
    assert not target.exists() and not sr._marker(target).exists(), f"[{case}] the refused boot created a store or a marker"


# --- 1. no wait declared: refused at once ----------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["writer", "read-only"])
def test_19_b_a_boot_that_finds_the_lock_held_and_no_wait_declared_is_refused_at_once_by_name(
    tmp_path: pathlib.Path, role: str
) -> None:
    """Another holds the lock and the manifest declares no wait: the boot returns while it is held, refused by name.

    Red on ``83af5650``: the boot was still inside ``load_and_boot``, refusing nothing, when the watch ended.
    """
    manifest, _registry, _records = p4e._deployment(tmp_path)
    target = tmp_path / "contended" / sr._STORE
    target.parent.mkdir()
    lock = _lock(target)
    signals = tmp_path / "signals"
    signals.mkdir()
    holder = _Holder(lock)
    try:
        booter = sr._another_process("boot", str(manifest), str(signals), str(target), role)
        sr._wait_for(signals / "starting", process=booter)
        finished_while_held = _finishes_within(booter, _AT_ONCE_WATCH_SECONDS)
    finally:
        holder.release()
    report = sr._report(booter)
    assert finished_while_held, (
        f"[{role}] a boot that found the store-creation lock held, with no wait declared, was still inside"
        f" load_and_boot {_AT_ONCE_WATCH_SECONDS:.0f} s later, refusing nothing; it must be refused at once, by name"
        f" (it returned only after the holder let go: {report.get('outcome')} {report.get('store_creation')})"
    )
    _assert_refused_lock_held(report, lock=lock, target=target, case=f"{role}, no wait declared")


# --- 2. a wait declared: waits that long, then refused ---------------------------------------------------------------


@pytest.mark.parametrize("role", ["writer", "read-only"])
def test_19_b_a_boot_with_a_declared_wait_waits_that_long_for_a_held_lock_then_is_refused_by_name(
    tmp_path: pathlib.Path, role: str
) -> None:
    """The manifest declares a short wait and the holder never lets go during the boot: it waits, then is refused."""
    manifest, _registry, _records = p4e._deployment(tmp_path)
    declaring = wb.manifest_declaring_a_wait(manifest, _SHORT_WAIT_SECONDS)
    target = tmp_path / "contended" / sr._STORE
    target.parent.mkdir()
    lock = _lock(target)
    signals = tmp_path / "signals"
    signals.mkdir()
    holder = _Holder(lock)
    try:
        booter = sr._another_process("boot", str(declaring), str(signals), str(target), role)
        sr._wait_for(signals / "starting", process=booter)
        finished_while_held = _finishes_within(booter, _SHORT_WAIT_SECONDS + _AT_ONCE_WATCH_SECONDS)
    finally:
        holder.release()
    report = sr._report(booter)
    assert finished_while_held, (
        f"[{role}] a boot with a declared wait of {_SHORT_WAIT_SECONDS} s was still waiting"
        f" {_SHORT_WAIT_SECONDS + _AT_ONCE_WATCH_SECONDS:.0f} s later; it must be refused once the wait has passed"
    )
    _assert_refused_lock_held(report, lock=lock, target=target, case=f"{role}, a declared wait")
    waited = (report["returned_ns"] - report["started_ns"]) / 1e9
    assert waited >= _SHORT_WAIT_SECONDS, (
        f"[{role}] the boot was refused after {waited:.2f} s, before the {_SHORT_WAIT_SECONDS} s its manifest declares"
    )
    assert wb.WAIT_SETTING in report["message"], (
        f"[{role}] the refusal's text must name the setting that bounded the wait: {report['message']}"
    )


# --- 3. a wait declared, the holder lets go within it: the boot proceeds ---------------------------------------------


def test_19_b_a_boot_with_a_declared_wait_proceeds_once_the_holder_lets_go_within_it(tmp_path: pathlib.Path) -> None:
    """The manifest declares a long wait; the holder lets go during it; the boot then creates and verifies the store."""
    manifest, _registry, _records = p4e._deployment(tmp_path)
    declaring = wb.manifest_declaring_a_wait(manifest, _LONG_WAIT_SECONDS)
    target = tmp_path / "contended" / sr._STORE
    target.parent.mkdir()
    lock = _lock(target)
    signals = tmp_path / "signals"
    signals.mkdir()
    holder = _Holder(lock)
    released_ns: int | None = None
    try:
        booter = sr._another_process("boot", str(declaring), str(signals), str(target), "writer")
        sr._wait_for(signals / "starting", process=booter)
        finished_while_held = _finishes_within(booter, _WAITING_WATCH_SECONDS)
    finally:
        released_ns = holder.release()
    report = sr._report(booter)
    assert not finished_while_held, (
        f"a boot with a declared wait of {_LONG_WAIT_SECONDS} s returned while the lock was still held, within"
        f" {_WAITING_WATCH_SECONDS} s; it must wait for the holder: {report}"
    )
    assert report["outcome"] == "booted", f"once the holder let go within the declared wait, the boot must boot: {report}"
    assert report["returned_ns"] > released_ns, "the boot returned before the holder let go"
    assert report["created_the_store"] is True and report["emptiness_reads"] == 1, (
        f"the boot must create the store and read it once: {report}"
    )
    assert report["store_creation"] == "verified", report


# --- 4. the config door carries the setting --------------------------------------------------------------------------


def test_19_b_the_config_door_carries_the_declared_wait_into_its_manifest_and_honors_it(tmp_path: pathlib.Path) -> None:
    """``ccf_config.yaml`` declares the wait; the derived manifest carries it; a held lock refuses after it, by name."""
    declared = DeploymentConfig.model_validate({**_config_document(), wb.WAIT_SETTING: _SHORT_WAIT_SECONDS})
    assert derive_deployment(declared, config_filename="ccf_config.yaml").manifest.store_creation_lock_wait_seconds == (
        _SHORT_WAIT_SECONDS
    ), "the manifest the config door derives does not carry the declared wait"
    silent = DeploymentConfig.model_validate(_config_document())
    assert derive_deployment(silent, config_filename="ccf_config.yaml").manifest.store_creation_lock_wait_seconds is None
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = write_artifact(config_dir, "ccf_config.yaml", {**_config_document(), wb.WAIT_SETTING: _SHORT_WAIT_SECONDS})
    target = tmp_path / "contended" / "config.sqlite3"
    target.parent.mkdir()
    lock = _lock(target)
    outcome: dict[str, Any] = {}

    def boot() -> None:
        started = time.monotonic()
        try:
            booted = load_config_and_boot(
                config_path, registry=ControlPlaneRegistry(), connection={"database_path": str(target)}
            )
        except BaseException as raised:  # noqa: BLE001 — the outcome is the measurement
            outcome["result"] = raised
        else:
            outcome["result"] = booted
            booted.handle.close()  # on this thread: SQLite binds a connection to the thread that opened it
        outcome["waited"] = time.monotonic() - started

    holder = _Holder(lock)
    worker = threading.Thread(target=boot)
    try:
        worker.start()
        worker.join(timeout=_SHORT_WAIT_SECONDS + _AT_ONCE_WATCH_SECONDS)
        finished_while_held = not worker.is_alive()
    finally:
        holder.release()
        worker.join(timeout=120)
    result = outcome.get("result")
    assert finished_while_held, "a config-door boot with a declared wait was still waiting long after it"
    assert type(result).__name__ == NOT_VERIFIED, f"refused, but not by {NOT_VERIFIED}: {result!r}"
    assert getattr(result, "reason", None) == "lock-held" and getattr(result, "lock", None) == lock, repr(result)
    assert outcome["waited"] >= _SHORT_WAIT_SECONDS, f"refused after {outcome['waited']:.2f} s, before the declared wait"
    assert not target.exists(), "the refused config-door boot created a store"


# --- 5. the setting: the deployment's own, typed, and the SDK supplies none -------------------------------------------


def _manifest_text(tmp_path: pathlib.Path) -> str:
    manifest, _registry, _records = p4e._deployment(tmp_path)
    return manifest.read_text(encoding="utf-8")


@pytest.mark.parametrize("written", ["0", "-1", "1.5", "true", '"5"'])
def test_19_b_a_declared_wait_that_is_not_a_positive_whole_number_of_seconds_is_refused_at_parse(
    tmp_path: pathlib.Path, written: str
) -> None:
    """Zero, a negative number, a fraction, a boolean and a quoted number: refused, on both documents.

    Each document is first parsed with a whole number of seconds, the positive control: a tree whose documents have no
    such field refuses every value, so the refusal alone would say nothing.
    """
    text = _manifest_text(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_text = write_artifact(config_dir, "ccf_config.yaml", _config_document()).read_text(encoding="utf-8")
    for document, artifact_class in ((text, DEPLOYMENT_MANIFEST), (config_text, DEPLOYMENT_CONFIG)):
        whole = load_artifact(f"{document}{wb.WAIT_SETTING}: 5\n", artifact_class)
        assert getattr(whole, wb.WAIT_SETTING) == 5, f"{artifact_class.class_id}: a whole number of seconds was not kept"
        with pytest.raises(ArtifactLoadError):
            load_artifact(f"{document}{wb.WAIT_SETTING}: {written}\n", artifact_class)


def test_19_b_the_wait_is_absent_unless_declared_and_kept_as_declared(tmp_path: pathlib.Path) -> None:
    """No SDK default: an absent field reads ``None`` on both documents; a declared one is kept."""
    text = _manifest_text(tmp_path)
    silent = load_artifact(text, DEPLOYMENT_MANIFEST)
    assert isinstance(silent, DeploymentManifest) and silent.store_creation_lock_wait_seconds is None
    declaring = load_artifact(f"{text}{wb.WAIT_SETTING}: 7\n", DEPLOYMENT_MANIFEST)
    assert isinstance(declaring, DeploymentManifest) and declaring.store_creation_lock_wait_seconds == 7
    quiet_config = parse_artifact(_config_document(), DEPLOYMENT_CONFIG)
    assert isinstance(quiet_config, DeploymentConfig) and quiet_config.store_creation_lock_wait_seconds is None
    declaring_config = parse_artifact({**_config_document(), wb.WAIT_SETTING: 7}, DEPLOYMENT_CONFIG)
    assert isinstance(declaring_config, DeploymentConfig) and declaring_config.store_creation_lock_wait_seconds == 7


@pytest.mark.parametrize("model", [DeploymentManifest, DeploymentConfig])
def test_19_b_a_document_declaring_no_wait_hashes_as_it_did_before_the_field_existed(
    tmp_path: pathlib.Path, model: type[Any]
) -> None:
    """Hash-transparent at ``None``: every document written before the field keeps its content address."""
    if model is DeploymentManifest:
        document = load_artifact(_manifest_text(tmp_path), DEPLOYMENT_MANIFEST)
    else:
        document = parse_artifact(_config_document(), DEPLOYMENT_CONFIG)
    transparent = hash_transparent_fields(model)
    assert wb.WAIT_SETTING in transparent, f"{model.__name__}.{wb.WAIT_SETTING} is not hash-transparent: {transparent}"
    before = {name: getattr(document, name) for name in model.model_fields if name not in transparent}
    assert content_hash(document) == content_hash(before), f"a {model.__name__} declaring no wait moved its address"
    declaring = document.model_copy(update={wb.WAIT_SETTING: 7})
    assert content_hash(declaring) != content_hash(document) and wb.WAIT_SETTING.encode() in canonical_bytes(declaring)
    assert wb.WAIT_SETTING.encode() not in canonical_bytes(document)


# --- 6. competing boots with no wait declared ------------------------------------------------------------------------


@pytest.mark.parametrize("roles", [("writer", "writer"), ("writer", "read-only")])
def test_19_b_two_plain_boots_racing_with_no_wait_declared_never_serve_a_store_they_did_not_verify(
    tmp_path: pathlib.Path, roles: tuple[str, str]
) -> None:
    """Free-running, two processes, twelve trials, each on a fresh path, with the manifest declaring no wait.

    Per trial: exactly one boot's adapter created the store; that boot read it once and booted ``"verified"``; the
    other read nothing and did not create it, and either reopened it ``"verified"``, or was refused as a second
    writer (``SingleWriterViolation``) or for the held lock (``lock-held``), never as stale; the marker reads
    ``verified``. A control (green before and after): on ``83af5650`` the other boot waited instead of refusing.
    """
    trials = 12
    manifest, _registry, _records = p4e._deployment(tmp_path)
    signals, stores = tmp_path / "signals", tmp_path / "stores"
    signals.mkdir()
    stores.mkdir()
    racing = [
        sr._another_process("race", str(manifest), str(signals), str(stores), str(role_id), role, str(trials))
        for role_id, role in enumerate(roles)
    ]
    reports = [sr._report(process, timeout=600) for process in racing]
    for trial in range(trials):
        pair = [report["trials"][trial] for report in reports]
        assert all("outcome" in each and each["outcome"] != "barrier-timed-out" for each in pair), pair
        created = [each for each in pair if each["created_the_store"]]
        assert len(created) == 1, f"[trial {trial}] exactly one boot must create the store: {pair}"
        creator = created[0]
        other = pair[1 - pair.index(creator)]
        assert creator["outcome"] == "booted" and creator["store_creation"] == "verified", f"[trial {trial}] {creator}"
        assert creator["emptiness_reads"] == 1, f"[trial {trial}] the boot that created the store must read it once: {creator}"
        assert other["emptiness_reads"] == 0, f"[trial {trial}] the boot that did not create the store must not read: {other}"
        if other["outcome"] == "booted":
            assert other["store_creation"] == "verified", f"[trial {trial}] {other}"
        elif other["raised"][0] == NOT_VERIFIED:
            assert other["reason"] == "lock-held", (
                f"[trial {trial}] the other boot may be refused for the held lock, never as stale: {other}"
            )
        else:
            assert other["raised"][0] == "SingleWriterViolation", (
                f"[trial {trial}] the other boot may only be refused as a second writer or for the held lock: {other}"
            )
        target = stores / str(trial) / sr._STORE
        assert sr._state(sr._marker(target)) == "verified", f"[trial {trial}] the marker must read verified"
