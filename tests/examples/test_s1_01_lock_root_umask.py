"""N-1 witness: s1-01's per-question lock roots pass PC3 under a group-writable umask (`D-IMPL-374`).

PC3 (panel C3; SEC-013) refuses, at connection validation, a
``writer_lease_lock_dir`` that is group- or world-writable. ``s1-01`` declares
each question's scratch root as that directory (``artifacts/backends.yaml``,
``per_run: path`` with ``filename: "."``), and ``run.py``'s ``ask_all`` created
the root with a plain ``mkdir``. On a host whose umask is ``0002`` the root came
out mode ``0775``, so every boot was refused with ``InvalidBackendConfig``
before any network call: ``make example-s1-01`` on both paths, the adoption
tests and the ``answers`` fixture (the scoped re-review's N-1, measured).

The witness is host-independent and offline. It forces umask ``0002`` (and
restores the previous one), drives ``ask_all`` exactly as ``main()`` does, and
points the declared Fluree variable at ``http://127.0.0.1:9``, where nothing
listens. The boot must get past config validation: failing later, at the
network step, is expected; failing with ``InvalidBackendConfig`` is the defect.
"""

from __future__ import annotations

import os
import pathlib
import stat
from collections.abc import Iterator

import pytest

from ccf.graph.registry import InvalidBackendConfig
from tests.examples.test_s1_01_output import _load_example

#: The variable ``artifacts/backends.yaml`` reads the Fluree URL from.
FLUREE_URL_VARIABLE = "CCF_TEST_FLUREE_URL"

#: Where nothing listens: the boot reaches the network step and fails there,
#: and no server is touched.
UNREACHABLE_FLUREE_URL = "http://127.0.0.1:9"

#: The umask the re-review measured on this host, under which ``mkdir`` makes a
#: group-writable directory.
GROUP_WRITABLE_UMASK = 0o002

#: The refusal PC3 raises for the defect, by its own wording.
GROUP_OR_WORLD_WRITABLE = "group- or world-writable"


@pytest.fixture
def group_writable_umask() -> Iterator[None]:
    """Umask ``0002`` for the test's duration; the previous umask restored after."""
    previous = os.umask(GROUP_WRITABLE_UMASK)
    try:
        yield
    finally:
        os.umask(previous)


def test_ask_all_gets_past_lock_directory_validation_under_a_group_writable_umask(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    group_writable_umask: None,
) -> None:
    # Positive control on the precondition: under this umask a plain `mkdir`
    # IS group-writable, so the run below exercises the defect's condition.
    probe = tmp_path / "umask-probe"
    probe.mkdir()
    assert stat.S_IMODE(probe.stat().st_mode) & 0o020, oct(probe.stat().st_mode)

    root = tmp_path / "run"
    root.mkdir(mode=0o700)
    monkeypatch.setenv(FLUREE_URL_VARIABLE, UNREACHABLE_FLUREE_URL)
    example = _load_example()
    requests = example.deployment.declared_questions()[:1]
    service_instants = example.deployment.declared_service_instants()[:1]

    failure: BaseException | None = None
    try:
        example.ask_all(
            root=root, requests=requests, service_instants=service_instants
        )
    except Exception as raised:  # noqa: BLE001 - classified below
        failure = raised

    assert not isinstance(failure, InvalidBackendConfig), (
        "the s1-01 boot was refused at connection validation under umask 0002:"
        f" {failure}"
    )
    assert failure is None or GROUP_OR_WORLD_WRITABLE not in str(failure), str(failure)
    # The question's lock root is owner-only, whatever the umask.
    lock_root = root / "q0"
    assert stat.S_IMODE(lock_root.stat().st_mode) == 0o700, oct(lock_root.stat().st_mode)
