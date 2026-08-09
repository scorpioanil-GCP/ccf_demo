"""Session-scoped per-rung fabric fixtures for the perf battery (PERF-02).

Boots real fabrics through the composition root (``ccf.boot.boot``) with a
``ControlPlaneRegistry`` populated from ``perf/synth/artifacts/*.yaml``, then
ingests the seeded envelope stream exclusively through
``handle.worker.ingest`` — the single-writer L1→L2 path (CLAUDE.md §10; no
lint-exempted shortcuts). SQLite backend under a session tmp dir.

Also importable as ``perf.conftest`` so the always-on determinism tests in
``tests/perf_synth`` can exercise :func:`build_fabric` without the perf tree
being collected (D-04).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

#: The perf battery's definition artifacts (D-09). All Control Plane keys and
#: every registered value are read from these files, never held as constants
#: in `/src` (CLAUDE.md §6.4).
ARTIFACTS = Path(__file__).resolve().parent / "synth" / "artifacts"

#: The rung ladder the session fixtures cover (D-07): fabric_1k / fabric_10k /
#: fabric_100k below. Rung sizes themselves live in perf.synth.generator.RUNGS.


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _resolution_spec(ontology: Any) -> Any:
    from ccf.assembly.worker import (
        EntityResolutionRule,
        EntityResolutionSpec,
        RelationshipResolutionRule,
    )

    return EntityResolutionSpec(
        semver=ontology["artifact_version"],
        entity_rules=tuple(
            EntityResolutionRule(
                match_key=rule["match_key"],
                entity_class=rule["entity_class"],
                identity_keys=tuple(rule["identity_keys"]),
                attribute_keys=tuple(rule.get("attribute_keys", ())),
            )
            for rule in ontology["entity_rules"]
        ),
        relationship_rules=tuple(
            RelationshipResolutionRule(
                relationship_type=rule["relationship_type"],
                subject_entity_class=rule["subject_entity_class"],
                object_entity_class=rule["object_entity_class"],
            )
            for rule in ontology["relationship_rules"]
        ),
    )


def boot_fabric(*, database_path: Path) -> "FabricHandle":
    """Boot an empty fabric from the perf artifacts — no ingestion.

    Extracted from :func:`build_fabric` so the fabric-scale assembly curve
    (11-03) can boot a fresh graph inside a pedantic ``setup`` callable and
    time *only* the ``handle.worker.ingest`` loop. The caller owns
    ``handle.close()``.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    ontology = _load("ontology.yaml")
    control = _load("controlplane.yaml")
    keys = control["keys"]

    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(
        keys["policy_bundle"], control["policy_bundle"]
    )
    return boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )


def build_fabric(*, rung: int, database_path: Path) -> "FabricHandle":
    """Boot a fabric from the perf artifacts and ingest one rung through L2.

    The only construction path the perf tree uses: composition-root boot,
    artifact-registered Control Plane state, and ``handle.worker.ingest`` for
    every envelope. The caller owns ``handle.close()``.
    """
    from perf.synth.generator import generate_events

    handle = boot_fabric(database_path=database_path)
    try:
        for envelope in generate_events(rung):
            handle.worker.ingest(envelope)
    except BaseException:
        handle.close()
        raise
    return handle


def _rung_fixture(rung: int, label: str) -> Any:
    @pytest.fixture(scope="session", name=f"fabric_{label}")
    def fixture(
        tmp_path_factory: pytest.TempPathFactory,
    ) -> Iterator["FabricHandle"]:
        handle = build_fabric(
            rung=rung,
            database_path=tmp_path_factory.mktemp("perf-fabric")
            / f"rung-{rung}.sqlite3",
        )
        try:
            yield handle
        finally:
            handle.close()

    return fixture


fabric_1k = _rung_fixture(1_000, "1k")
fabric_10k = _rung_fixture(10_000, "10k")
fabric_100k = _rung_fixture(100_000, "100k")
