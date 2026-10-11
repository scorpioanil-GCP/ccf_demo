# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A plain boot of one store path, run in its own process, for the deployment-marker tests (SEC-020, D-IMPL-378 1.1/1.2).

Run by ``tests/products/test_deployment_marker_owned_and_crash_safe.py`` and
``tests/products/test_deployment_marker_serialized_and_stale_refused.py`` as
``python -B -m tests.products._plain_boot_from_another_process <mode> <manifest> <signals> <store> [...]`` from
the repository root, with ``PYTHONPATH`` naming the tree's ``src`` and
``runtime``. It builds its own Control Plane registry from the deployment's
documents, as a second worker process of the deployment would, and boots the
store plainly (``load_and_boot`` with ``for_question`` left ``False``). Not
collected by pytest (no ``test_`` prefix). Every domain value here is fixture
vocabulary (CINV-01, CLAUDE.md §11).

What it observes, through names that exist on a tree with or without the
repairs (so a tree without them fails on its behavior, never on an import):
``ccf.deployment.manifest.boot`` is wrapped to note whether the store existed
when the boot reached it (so whether this boot's adapter created it), and the
governed reader's ``as_of`` is wrapped to count reads at the latest instant a
timestamp can name (the boot's emptiness read). The report is one JSON object
on the last line of stdout; for a refusal it carries the refusal's class names
(its MRO), its ``reason``, its ``lock`` (a path, where the refusal names one)
and its text.

Modes:

* ``crash-before-boot`` — inside the boot, after the deployment marker exists
  and before the adapter opens the store, the process kills itself with
  ``SIGKILL``: no ``finally`` runs, as in a power cut or an OOM kill.
* ``crash-after-boot`` — inside the boot, after the adapter created and opened
  the store and before the boot's emptiness read, the process kills itself
  with ``SIGKILL``.
* ``crash-during-read`` — inside the boot's emptiness read (the governed
  reader's ``as_of`` at the latest instant), before it returns, the process
  kills itself with ``SIGKILL``.
* ``pause-inside-boot`` — inside the boot, before the adapter opens the store,
  writes ``<signals>/inside`` and waits for ``<signals>/release``; then boots,
  reports and closes.
* ``boot`` (``<read-only|writer>``) — writes ``<signals>/starting``, boots
  once, reports and closes.
* ``race`` (``<role-id> <read-only|writer> <trials>``) — for each trial ``t``,
  meets the other racing process at a two-party barrier in ``<signals>/<t>``,
  boots ``<store>/<t>/graph.sqlite3``, closes, and reports every trial.
"""

from __future__ import annotations

import json
import os
import pathlib
import signal
import sys
import time
from datetime import UTC, datetime
from typing import Any

#: The latest instant a timestamp can name: the instant a boot's emptiness read is taken at.
_LATEST = datetime.max.replace(tzinfo=UTC)

#: How long a paused or racing process waits for its counterpart before giving up (a test-side bound).
_WAIT_SECONDS = 120.0


def _wait_for(*paths: pathlib.Path) -> bool:
    deadline = time.monotonic() + _WAIT_SECONDS
    while not all(path.exists() for path in paths):
        if time.monotonic() > deadline:
            return False
        time.sleep(0.0005)
    return True


def _marker_text(store: pathlib.Path) -> str | None:
    marker = pathlib.Path(f"{store.resolve()}.ccf-deployment-store")
    try:
        return marker.read_text(encoding="utf-8")
    except OSError:
        return None


class _Observed:
    """The two wrappers, installed once per process, and what they saw during the current boot."""

    def __init__(self, mode: str, signals: pathlib.Path) -> None:
        import ccf.deployment.manifest as manifest_module  # noqa: PLC0415
        from ccf.graph import governed_reader  # noqa: PLC0415

        self.store: pathlib.Path | None = None
        self.created_the_store: bool | None = None
        self.emptiness_reads = 0
        self.boot_entered_ns: int | None = None
        real_boot = manifest_module.boot
        reader_class = governed_reader._ClassificationGovernedReader
        real_as_of = reader_class.as_of
        observed = self

        def observed_boot(**kwargs: Any) -> Any:
            observed.boot_entered_ns = time.monotonic_ns()
            store = pathlib.Path(str(kwargs["connection"]["database_path"]))
            observed.created_the_store = not store.exists()
            if mode == "crash-before-boot":
                os.kill(os.getpid(), signal.SIGKILL)
            if mode == "pause-inside-boot":
                (signals / "inside").write_text("inside the boot, before the adapter opens the store\n")
                _wait_for(signals / "release")
            handle = real_boot(**kwargs)
            if mode == "crash-after-boot":
                os.kill(os.getpid(), signal.SIGKILL)
            return handle

        def observed_as_of(self: Any, *, tenant_id: str, at: datetime) -> Any:
            if at == _LATEST:
                observed.emptiness_reads += 1
                if mode == "crash-during-read":
                    os.kill(os.getpid(), signal.SIGKILL)
            return real_as_of(self, tenant_id=tenant_id, at=at)

        manifest_module.boot = observed_boot
        reader_class.as_of = observed_as_of

    def reset(self) -> None:
        self.created_the_store = None
        self.emptiness_reads = 0
        self.boot_entered_ns = None


def _boot_once(observed: _Observed, manifest: pathlib.Path, registry: Any, store: pathlib.Path, *, read_only: bool) -> dict[str, Any]:
    from ccf.deployment import load_and_boot  # noqa: PLC0415

    observed.reset()
    report: dict[str, Any] = {"store": str(store), "read_only": read_only, "started_ns": time.monotonic_ns()}
    try:
        fabric = load_and_boot(
            manifest, registry=registry, connection={"database_path": str(store)}, read_only=read_only
        )
    except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
        report.update(
            returned_ns=time.monotonic_ns(),
            outcome="raised",
            raised=[klass.__name__ for klass in type(raised).__mro__],
            reason=getattr(raised, "reason", None),
            lock=None if getattr(raised, "lock", None) is None else str(raised.lock),
            message=str(raised),
        )
    else:
        report.update(
            returned_ns=time.monotonic_ns(),
            outcome="booted",
            store_creation=fabric.store_creation,
            question_store=fabric.question_store,
        )
        fabric.handle.close()
    report.update(
        boot_entered_ns=observed.boot_entered_ns,
        created_the_store=observed.created_the_store,
        emptiness_reads=observed.emptiness_reads,
        marker_after=_marker_text(store),
    )
    return report


def main(argv: list[str]) -> dict[str, Any]:
    from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: PLC0415

    mode, manifest, signals, store = argv[0], pathlib.Path(argv[1]), pathlib.Path(argv[2]), pathlib.Path(argv[3])
    import ccf  # noqa: PLC0415 — which tree this process measured

    observed = _Observed(mode, signals)
    registry = ControlPlaneRegistry()
    result: dict[str, Any] = {"imported": str(pathlib.Path(ccf.__file__).resolve()), "mode": mode}
    if mode == "race":
        role, read_only, trials = argv[4], argv[5] == "read-only", int(argv[6])
        reports = []
        for trial in range(trials):
            meeting = signals / str(trial)
            meeting.mkdir(parents=True, exist_ok=True)
            (meeting / f"ready-{role}").write_text("ready\n")
            if not _wait_for(meeting / "ready-0", meeting / "ready-1"):
                reports.append({"trial": trial, "outcome": "barrier-timed-out"})
                break
            target = store / str(trial) / "graph.sqlite3"
            target.parent.mkdir(parents=True, exist_ok=True)
            reports.append({"trial": trial, **_boot_once(observed, manifest, registry, target, read_only=read_only)})
        result["trials"] = reports
        return result
    read_only = len(argv) > 4 and argv[4] == "read-only"
    if mode == "boot":
        (signals / "starting").write_text("about to boot\n")
    result.update(_boot_once(observed, manifest, registry, store, read_only=read_only))
    return result


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1:])))
