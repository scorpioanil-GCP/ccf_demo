"""SEC-009 ruling 2 — the in-process adapter's store is composed with the erasure consult (`D-IMPL-374` (4)).

RED originally: ``ccf.client.adapters.inprocess._boot`` handed the resolver a raw
``FileArtifactStore`` that served erased bytes.

Fix round 5: the consult verifies every erasure against the erasure authority
the deployment DECLARES in its binding document (its HITL policy key, its
erasure workflow's content hash, the erasure door's public key). The shared
fixture declares none (``erasure_authority: {}``), so this control declares the
test authority in its private copy before booting — what a deployment that runs
an erasure door states.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from ccf.client.adapters.binding_document import load_binding_document
from ccf.client.adapters.inprocess import _boot
from tests.composition import declared_erasure_authority
from tests.erasure import composed

#: The fixture deployment's tenant (``tests/client/fixtures/deployment/ccf_config.yaml``).
FIXTURE_TENANT = "tenant-client-fixture"


def _declare_the_test_erasure_authority(root: Path) -> None:
    authority = declared_erasure_authority(FIXTURE_TENANT)
    path = root / "binding.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["erasure_authority"] = {
        # Bare, as a deployment writes it: the adapter confines it to the tenant at boot.
        "hitl_policy_key": authority.hitl_policy_key.partition("/")[2],
        "workflow_definition_hash": authority.workflow_definition_hash,
        "door_keys": {kid: dict(jwk) for kid, jwk in authority.door_keys.items()},
    }
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_the_inprocess_adapters_store_composes_the_consult(seeded_root: Path) -> None:
    _declare_the_test_erasure_authority(seeded_root)
    booted = _boot(load_binding_document(seeded_root), clock=lambda: datetime(2026, 7, 30, tzinfo=UTC))
    store = booted.resolver.artifact_store
    assert store.tenant_id == FIXTURE_TENANT
    assert store.erasure_trust.authority_for(FIXTURE_TENANT) == declared_erasure_authority(FIXTURE_TENANT)
    composed.assert_consults(store, store.index, control_plane=store.control_plane, tenant=store.tenant_id)
