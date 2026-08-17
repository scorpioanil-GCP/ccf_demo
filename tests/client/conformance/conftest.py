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

from tests.client.conformance.suite import Provision
from tests.client.conftest import FIXTURE_DEPLOYMENT, seed


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
    """
    handed_out = 0

    def make(name: str) -> Path:
        nonlocal handed_out
        root = tmp_path / f"{handed_out:02d}-{name}" / "deployment"
        handed_out += 1
        shutil.copytree(FIXTURE_DEPLOYMENT, root)
        seed(root)
        return root

    return make
