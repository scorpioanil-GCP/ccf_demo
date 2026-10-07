"""PM10 (panel C10): a failure after boot's guarded block must not strand the writer or its lease (SEC-013 x SEC-023; `D-IMPL-374`).

The cross-AI panel measured it (probe ``probe_b6_boot_strand.py``):
``ccf.boot.boot`` guarded only the worker build. The SEC-023 authority wrap
(``governed_reader(store.reader, _mint_authority_of(spec))``) and the
:class:`~ccf.boot.FabricHandle` construction ran after that guard, so a raise
there left the minted writer live in this process's table and its SQLite
cross-process lease held: a corrected retry in this process was refused with
``SingleWriterViolation``, and every other process stayed locked out until
this one exited. Every step after the mint must give the graph back on failure.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import Any

import pytest

import ccf.boot as boot_module
from ccf.assembly.worker import EntityResolutionSpec
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.composition import register_at_composition


def _arguments(database: Path) -> dict[str, Any]:
    spec = EntityResolutionSpec.model_validate(
        {
            "semver": "1.0.0",
            "entity_rules": [
                {
                    "match_key": "acct_ref",
                    "entity_class": "account",
                    "identity_keys": ["acct_ref"],
                    "attribute_keys": ["tier"],
                    "attribute_authorities": {"tier": ["core"]},
                }
            ],
        }
    )
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, "test/pm10-spec", spec)
    policy_version = register_at_composition(registry, "test/pm10-policy", {"regime": "pm10"})
    return dict(
        backend="sqlite",
        connection={"database_path": database},
        registry=registry,
        resolution_spec_key="test/pm10-spec",
        resolution_spec_version=spec_version,
        policy_bundle_key="test/pm10-policy",
        policy_bundle_version=policy_version,
        tenant_ids=("pm10-tenant",),
    )


def _lease_is_free(database: Path) -> bool:
    """Whether the SQLite store's cross-process lease file can be locked right now.

    A second open file description: ``flock`` conflicts between descriptions
    even inside one process, so this reads exactly what another process would.
    """
    sidecar = Path(f"{database}.ccf-writer.lock")
    if not sidecar.exists():
        return True
    descriptor = os.open(sidecar, os.O_RDWR)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        return True
    finally:
        os.close(descriptor)


@pytest.mark.parametrize(
    "failing_step",
    ["_mint_authority_of", "FabricHandle"],
)
def test_a_failure_after_the_worker_build_gives_back_the_writer_and_its_lease(
    failing_step: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "graph.sqlite3"
    arguments = _arguments(database)

    def failing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"simulated failure in {failing_step}")

    with monkeypatch.context() as patched:
        patched.setattr(boot_module, failing_step, failing)
        with pytest.raises(RuntimeError, match="simulated failure"):
            boot_module.boot(**arguments)

    # The cross-process lease was given back with the failed boot...
    assert _lease_is_free(database), "the failed boot left the store's writer lease held"
    # ...and the corrected retry in THIS process boots rather than being refused
    # as a second writer.
    handle = boot_module.boot(**arguments)
    try:
        assert handle.lease_scope == "cross-process"
    finally:
        handle.close()
    assert _lease_is_free(database)
