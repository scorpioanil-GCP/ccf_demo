# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Another process's routes into a question's store, run while the question is using it (SEC-020 P4s-A (b)).

Run by ``tests/products/test_question_store_empty_at_boot_and_held_through_use.py``
as ``python -B -m tests.products._question_store_routes_from_another_process
<manifest> <store path> <records directory>`` from the repository root. It
builds its own Control Plane registry from the same deployment documents, as a
second worker process of the deployment would, tries each route once and
prints one JSON object: for each route, the class names of what it raised (its
type's MRO), or what it returned. Not collected by pytest (no ``test_``
prefix). Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections.abc import Callable
from typing import Any

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from tests.composition import declare_wide_temporal_boundary, declaring_store
from tests.products import test_withheld_subject_population_composite_and_fabric as m
from tests.support.sqlite_lease import lock_dir_beside


def _outcome(attempt: Callable[[], Any]) -> dict[str, Any]:
    try:
        returned = attempt()
    except Exception as raised:  # noqa: BLE001 — the outcome is the measurement
        return {"raised": [klass.__name__ for klass in type(raised).__mro__]}
    return {"returned": str(returned)}


def main(manifest: pathlib.Path, path: pathlib.Path, records: pathlib.Path) -> dict[str, Any]:
    registry = ControlPlaneRegistry()
    connection = {"database_path": str(path), "writer_lease_lock_dir": lock_dir_beside(str(path))}

    def a_question_boot() -> str:
        load_and_boot(manifest, registry=registry, connection=connection, for_question=True).handle.close()
        return "booted"

    def a_plain_writer_boot() -> str:
        fabric = load_and_boot(manifest, registry=registry, connection=connection)
        try:
            for envelope in m._base_accounts():
                fabric.handle.worker.ingest(envelope)
        finally:
            fabric.handle.close()
        return "booted and wrote"

    def a_plain_read_only_boot_asked_a_question() -> str:
        fabric = load_and_boot(manifest, registry=registry, connection=connection, read_only=True)
        try:
            declare_wide_temporal_boundary(registry, tenant_id=fabric.tenant_id)
            store = declaring_store(records, m.REPLAY_RECORD_CLASS, m.QUERY_PIN_CLASS, ADMITTED_CHILD_CONTRACT_CLASS)
            return type(
                m._ask(m._governed((fabric, registry, store), plan_factory=m._late(), acquisition=None), m.sec020.MISSING)
            ).__name__
        finally:
            fabric.handle.close()

    import ccf  # noqa: PLC0415 — which tree this process measured

    return {
        "imported": str(pathlib.Path(ccf.__file__).resolve()),
        "a boot for a question at its path": _outcome(a_question_boot),
        "a plain writer boot at its path": _outcome(a_plain_writer_boot),
        "a plain read-only boot at its path, asked a governed question": _outcome(a_plain_read_only_boot_asked_a_question),
    }


if __name__ == "__main__":
    print(json.dumps(main(*(pathlib.Path(argument) for argument in sys.argv[1:4]))))
