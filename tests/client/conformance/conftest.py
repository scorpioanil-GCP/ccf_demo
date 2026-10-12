# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The deployments the conformance legs speak to — one per subject, per test.

Shared by the binding module and by the controls, which is why it is a
``conftest`` rather than a helper in either: both need the same provisioning
discipline, and a copy in one of them is a copy that can drift from the other.

**One root per subject, never a shared one.** Parity across transports has to
be a claim about two transports answering independently, and sharing one
deployment would make it a claim about one graph read twice. It is not open to
the suite anyway: a second boot against one graph is a second writer, and
``ccf.graph._writer`` refuses it by name.

The parent ``tests/client/conftest.py`` supplies the always-on fixture
deployment, the seeding, and the autouse boot-cache reset that this package
depends on — the reset applies here because a ``conftest`` covers its whole
subtree.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.client.adapters.binding_document import load_binding_document

from tests.client.conformance.suite import Provision
from tests.client.conftest import FIXTURE_DEPLOYMENT, seed
from tests.client.fixtures import (
    PINNED_SERVED_AT,
    SERVED_AT_ENV,
    STDIO_SERVER,
    declare_server,
)


@pytest.fixture()
def provision(tmp_path: Path) -> Provision:
    """Hand out a fresh, already-populated deployment root per name.

    Populated **before** any client exists, which is ``D-16`` satisfied by
    construction: the deployment an address names is already populated when a
    client reaches it, and a client call that ingested would make asking a
    question a producer-side act.

    **Every call gets a distinct directory**, counter first, so two subjects
    sharing one graph is impossible rather than merely refused. The name is
    carried into the path so a failure names a directory a reader can go and
    look at, and the counter is what lets a single test run two legs without
    the second one inheriting the first one's deployments.

    Two subjects answering to the *same name* is a different hazard and is
    refused where it belongs — in
    :func:`~tests.client.conformance.suite._ask_each`, which is the thing that
    would otherwise report one transport's answer under another's name.

    **The server program is copied into the copied root's PARENT**, because that
    is where ``binding.yaml``'s ``server:`` key resolves (``D-10``). The
    committed fixture and its program are already in that relationship; a copy
    that took only the deployment would inherit a declaration pointing at
    nothing, and a leg refused for a missing program is indistinguishable from
    one refused for a deployment that declared none.

    **And it reads a provisioned root's records, as that deployment's
    operator** (E1 (a), ``D-IMPL-378``): ``read_record`` resolves a replay
    reference against the artifact store the root's own ``binding.yaml``
    declares — the store every transport over that root writes to — and returns
    the record's bytes. ``suite.assert_served_parity`` compares ``replay_ref`` by
    that record, modulo its per-answer issuance.
    """
    return _Provisioner(tmp_path)


class _Provisioner:
    """The conformance package's :class:`~tests.client.conformance.suite.Provision`."""

    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path
        self._handed_out = 0

    def __call__(self, name: str) -> Path:
        root = self._tmp_path / f"{self._handed_out:02d}-{name}" / "deployment"
        self._handed_out += 1
        shutil.copytree(FIXTURE_DEPLOYMENT, root)
        shutil.copy2(STDIO_SERVER, root.parent)
        declare_server(root, root.parent / STDIO_SERVER.name)
        seed(root)
        return root

    def read_record(self, root: Path, reference: str) -> bytes:
        document = load_binding_document(root)
        store = FileArtifactStore(
            root=document.artifact_store,
            write_kinds=WriteKinds.declare({document.replay_record_class: (ReplayMint,)}),
        )
        return store.get(content_address=store.resolve_uri(uri=reference))


@pytest.fixture(autouse=True)
def _pin_the_serving_instant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Export the pinned instant so a CHILD-process subject inherits it.

    `D-IMPL-358` step 5. The in-process subject is composed with the pin
    directly; the `mcp+stdio` subject is a separate process and can be reached
    only through the environment, which its adapter passes on deliberately
    (`env=dict(os.environ)`). Autouse because every leg in this package compares
    subjects to each other, and a leg that pinned one side only would compare a
    pinned answer against a live one and report the difference as a transport
    disagreement.

    `monkeypatch` so the export dies with the test rather than leaking into
    whatever runs next in this process.
    """
    monkeypatch.setenv(SERVED_AT_ENV, PINNED_SERVED_AT.isoformat())
