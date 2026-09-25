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
from datetime import UTC, datetime
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


#: The fixed instant every perf composition decision is recorded at, so the
#: capability's ``decision_id`` is the same bytes on every run.
COMPOSED_AT = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _composition_capability(registry: Any, kind: Any, *, tenant: str, resource: str) -> Any:
    """Mint one composition kind for one resource, the decision recorded first.

    The perf tree boots its fabrics as a deployment would: it is the
    composition root of the graphs it times, and a composition root registers
    its own Control Plane entries under ``Register`` minted for ONE key — and
    hands its replay writer ``ReplayMint`` for ONE evidence class — after
    recording the decision on the registry's audit log (D-IMPL-354). The
    capability comes from :func:`ccf.authz.capability.mint_at_composition`,
    the only producer of a composition kind; nothing here names the sentinel.
    """
    from ccf.authz.capability import COMPOSITION_PRINCIPAL, mint_at_composition
    from ccf.contracts.canonical import content_hash

    event = registry.audit_log.append(
        action="composition",
        key=resource,
        version=kind.action_id,
        resolved=True,
        occurred_at=COMPOSED_AT,
        actor=COMPOSITION_PRINCIPAL,
    )
    return mint_at_composition(
        kind,
        tenant=tenant,
        principal=COMPOSITION_PRINCIPAL,
        resource=resource,
        decision_id=content_hash(event),
    )


def _register_capability(registry: Any, key: str) -> Any:
    from ccf.authz.capability import Register

    return _composition_capability(
        registry, Register, tenant=key.partition("/")[0], resource=key
    )


def register_at_composition(registry: Any, key: str, artifact: object) -> str:
    """``registry.register`` under a composition-minted ``Register`` for ``key``."""
    return registry.register(_register_capability(registry, key), artifact)


def register_typed_at_composition(
    registry: Any, key: str, artifact: object, artifact_class: Any
) -> str:
    """``registry.register_typed`` under a composition-minted ``Register`` for ``key``."""
    return registry.register_typed(_register_capability(registry, key), artifact, artifact_class)


def register_versioned_at_composition(
    registry: Any, key: str, artifact: object, artifact_class: Any
) -> Any:
    """``registry.register_versioned`` under a composition-minted ``Register`` for ``key``."""
    return registry.register_versioned(
        _register_capability(registry, key), artifact, artifact_class
    )


def execute_capability(*, tenant: str, resource: str) -> Any:
    """``Authorized[Execute]`` for ``tenant`` on the workflow key ``resource``.

    ``WorkflowFactory.construct`` takes the definition key from the capability
    (D-IMPL-353 §1.2), so the benchmark holds the capability a served caller
    would hold: minted by :func:`ccf.authz.capability.mint` from an *allowed*
    decision for exactly this tenant, action and key — the gate's own path,
    not a fabrication. The decision id names no real audit event; the perf
    tree measures construction, not authorization.
    """
    from ccf.authz.actions import ACTION_WORKFLOW_INVOKE
    from ccf.authz.capability import Execute, mint
    from ccf.authz.decision import AuthzDecision

    decision = AuthzDecision(
        allowed=True,
        matched_scope_pattern=tenant,
        matched_resource_pattern=resource,
        artifact_version="1.0.0",
        action_id=ACTION_WORKFLOW_INVOKE,
        tenant=tenant,
        resource=resource,
    )
    return mint(
        Execute, decision=decision, principal="perf-battery", decision_id="authz-decision-perf"
    )


def replay_mint_at_composition(registry: Any, *, tenant: str, artifact_class: str) -> Any:
    """The composition root's ``ReplayMint`` for ``artifact_class`` under ``tenant``."""
    from ccf.authz.capability import ReplayMint

    return _composition_capability(registry, ReplayMint, tenant=tenant, resource=artifact_class)


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
    spec_version = register_at_composition(
        registry, keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = register_at_composition(
        registry, keys["policy_bundle"], control["policy_bundle"]
    )
    return boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
        # D-IMPL-354: the tenant(s) this test composes the fabric for.
        tenant_ids=(ontology["tenant_id"],),
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
