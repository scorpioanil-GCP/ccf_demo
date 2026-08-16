"""The always-on deployment the client conformance suite boots.

**Network-free and credential-free by construction.** The fixture deployment
under ``fixtures/deployment/`` declares a file-backed reference store and
composes its connection from a *path*, never from an environment read — so this
suite passes with ``CCF_TEST_POSTGRES_DSN``, ``NEO4J_URI``, ``MONGO_URI`` and
``FLUREE_URL`` all unset. That property is the whole reason the fixture exists:
``D-32`` keeps the *example*'s deployment pointed at already-populated stores
outside the repository, which cannot run in the always-on pipeline, and a parity
gate that only runs when someone opts in protects nothing.

**Seeding happens here, at fixture setup, before any client exists** — which is
how ``D-16`` is satisfied by construction rather than by inspection. The
deployment an address names is already populated when a client reaches it; a
client call that ingested would make asking a question a producer-side act, and
``test_no_provisioning.py`` is the gate that says so. ``D-32``'s prohibition is
on committing demo data to ``examples/``; a test fixture under ``tests/`` is a
different thing, and this docstring says so rather than leaving a later reader
to assume otherwise.

Each test gets a **private copy** of the committed deployment. Copying rather
than sharing is what makes the root — and therefore the graph, and therefore the
single-writer identity — per-test, so a test that boots cannot make the next one
fail for a reason belonging to it.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.config import load_config_and_boot
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

#: The committed deployment every test copies. One authored deployment, so a
#: second copy is never a second thing to keep in step.
FIXTURE_DEPLOYMENT = Path(__file__).parent / "fixtures" / "deployment"

#: The instant the fixture's rows are observed at, and the instant its
#: ``scenario.yaml`` names as the default ``asked_at``. Data, never a clock
#: read — which is what makes every assertion in this suite reproducible.
SEEDED_AT = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)

#: The rows the fixture graph holds. Test data, so it lives test-side; the
#: **attribute names** it is keyed by are read from the deployment's own
#: document, so the two cannot drift.
SEEDED_ROWS: tuple[tuple[str, str], ...] = (
    ("alpha", "10"),
    ("beta", "50"),
    ("gamma", "90"),
)


def scenario_document(root: Path) -> Mapping[str, Any]:
    """The deployment's own vocabulary document, parsed."""
    return cast(
        Mapping[str, Any],
        yaml.safe_load((root / "scenario.yaml").read_text(encoding="utf-8")),
    )


def config_document(root: Path) -> Mapping[str, Any]:
    """The deployment's Control Plane document, parsed."""
    return cast(
        Mapping[str, Any],
        yaml.safe_load((root / "ccf_config.yaml").read_text(encoding="utf-8")),
    )


@pytest.fixture()
def deployment_root(tmp_path: Path) -> Path:
    """A private, unseeded copy of the committed fixture deployment."""
    root = tmp_path / "deployment"
    shutil.copytree(FIXTURE_DEPLOYMENT, root)
    return root


def seed(root: Path, rows: tuple[tuple[str, str], ...] = SEEDED_ROWS) -> None:
    """Populate a deployment's graph, then release its writer.

    Boots, ingests one envelope per row through ``handle.worker``, and
    **closes**. Closing is not tidiness: the writer is held per graph
    (``ccf.graph._writer::_LIVE_WRITERS``), so a seed that stayed open would
    make the client's own boot raise
    :class:`~ccf.graph._writer.SingleWriterViolation` — and the test would be
    measuring the seed's failure to let go rather than anything about the
    client.

    The attribute names come from the deployment's ``scenario.yaml`` and the
    entity class from its ``ccf_config.yaml``, so this function names no
    vocabulary of its own.
    """
    scenario = scenario_document(root)
    attributes = scenario["attributes"]
    storage = scenario["storage"]
    registry = ControlPlaneRegistry()
    booted = load_config_and_boot(
        root / "ccf_config.yaml",
        registry=registry,
        connection={"database_path": str(root / storage["graph_filename"])},
    )
    try:
        for index, (name, score) in enumerate(rows):
            booted.handle.worker.ingest(
                SignalEnvelope(
                    tenant_id=booted.tenant_id,
                    envelope_id=f"widget/{index}",
                    source=SourceIdentity(system_id="widgets"),
                    ingestion_timestamp=SEEDED_AT,
                    observed_time=SEEDED_AT,
                    raw_payload={
                        attributes["reference"]: str(index),
                        attributes["name"]: name,
                        attributes["score"]: score,
                    },
                )
            )
    finally:
        booted.handle.close()


@pytest.fixture()
def seeded_root(deployment_root: Path) -> Path:
    """A private deployment copy whose graph is already populated.

    The ordinary fixture for a client test: by the time a client exists, the
    deployment it will reach has been populated and its writer released.
    """
    seed(deployment_root)
    return deployment_root
