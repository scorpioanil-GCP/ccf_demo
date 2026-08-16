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

    A repeated name is refused rather than served the same directory twice. A
    leg that provisioned one root for two subjects would compare a transport
    against itself and report parity it never measured — the defect this whole
    package exists to be immune to.
    """
    handed_out: set[str] = set()

    def make(name: str) -> Path:
        if name in handed_out:
            raise AssertionError(
                f"a deployment root was already provisioned under the name"
                f" `{name}` — handing the same root to two subjects would have"
                " them compare one graph against itself and report parity that"
                " was never measured"
            )
        handed_out.add(name)
        root = tmp_path / name / "deployment"
        shutil.copytree(FIXTURE_DEPLOYMENT, root)
        seed(root)
        return root

    return make
