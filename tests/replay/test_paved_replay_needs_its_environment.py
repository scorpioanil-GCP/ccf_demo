"""Replaying a paved product's record needs the replay environment built first (`D-IMPL-378` R-A2 (a)).

Ruling R-A2 (a), Dave, 2026-10-08 12:29 MST: *"Document the supported
replay-environment path."* After R-A (b) a process that builds its replay
environment replays earlier records with nothing asked
(``tests/replay/test_fresh_process_replay.py``). A process that only OPENS a
paved product does not: ``src/ccf/products/product.py::open_product`` boots
nothing, so the Control Plane it holds carries none of the declarations a record
pins until something boots a fabric over it.

What is asserted, over one paved tree and one store:

1. **The limitation the documentation states.** A later opening, over a Control
   Plane of its own, that asks nothing and builds no environment is refused at
   the first pinned binding it cannot resolve, ``ReplayUnresolvable``.
2. **The supported path.** The same opening, after booting the substrate the
   record was answered on (read-only, through ``load_config_and_boot`` over its
   documents and its Control Plane) and building
   ``src/ccf/replay/environment.py::RecordedEnvironment``, reconstructs the
   record, asking nothing and filing no new record.

A fresh Control Plane per opening is the paved road's whole per-process state:
the store is on disk and the fabric is booted per question, so a second opening
in this process faithfully models a process started later.
"""

from __future__ import annotations

import pathlib

import pytest

from ccf.deployment import load_config_and_boot
from ccf.replay.engine import ReplayUnresolvable, replay_refusal
from ccf.replay.environment import RecordedEnvironment
from ccf.replay.record import DecisionReplayRecord
from ccf.products.refusal import RefusalEnvelope

from tests.products import test_paved_road as paved
from tests.support.sqlite_lease import lock_dir_beside


def _records(scratch: pathlib.Path) -> set[pathlib.Path]:
    return {path for path in (scratch / "artifact-store").rglob("*") if path.is_file()}


def test_an_opened_product_replays_an_earlier_record_only_after_its_environment_is_built(
    tmp_path: pathlib.Path,
) -> None:
    root = paved._write_tree(tmp_path / "paved")
    scratch = tmp_path / "scratch"
    with paved._open(root, scratch) as opened:
        refused = opened.answer(paved._question(opened, no_such_parameter=1))
        assert isinstance(refused, RefusalEnvelope), refused
        address = opened.artifact_store.resolve_uri(uri=refused.replay_reference)

    acquisition = paved._Acquire()
    with paved._open(root, scratch, acquire=acquisition) as reopened:
        filed = _records(scratch)
        assert filed, "the store holds no record to replay; the comparison below would be vacuous"
        # 1. Opened only: the Control Plane holds none of what the record pins.
        with pytest.raises(ReplayUnresolvable) as unresolvable:
            replay_refusal(
                record_address=address,
                store=reopened.artifact_store,
                reader=None,
                control_plane=reopened.control_plane,
                environment=None,
            )
        assert "is not registered" in str(unresolvable.value), unresolvable.value

        # 2. The supported path: boot the recorded substrate read-only, build the environment, replay.
        record = DecisionReplayRecord.model_validate_json(reopened.artifact_store.get(content_address=address))
        minted = max(scratch.glob("paved_fixture_*.sqlite3"), key=lambda path: path.stat().st_mtime_ns)
        fabric = load_config_and_boot(
            reopened.config_path,
            registry=reopened.control_plane,
            connection={"database_path": str(minted), "writer_lease_lock_dir": lock_dir_beside(str(minted))},
            read_only=True,
        )
        try:
            environment = RecordedEnvironment(record=record, opened=reopened, fabric=fabric)
            replay_refusal(
                record_address=address,
                store=reopened.artifact_store,
                reader=None,
                control_plane=reopened.control_plane,
                environment=environment,
            )
        finally:
            fabric.handle.close()
        assert _records(scratch) == filed, "building the environment or replaying filed something"
        assert acquisition.contexts == [], "building the environment or replaying acquired something"
