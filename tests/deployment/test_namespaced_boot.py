"""The config loader's derived keys live under the deployment's tenant (D-IMPL-354).

The paved road derives a section's Control Plane key from its label —
``product_class``, ``policy``, ``half_life`` — and the binding document names
them the same way. Under the key grammar the registry enforces
(``{tenant}/{class}[/{name}]``, D-IMPL-353 §1.3) a bare key belongs to
nobody and no capability can register it. The loader is SDK mechanism, so
it is the loader that places every derived key under the tenant it resolved
before it mints, registers or composes — and refuses, before minting, a key
an author placed under another tenant.
"""

from __future__ import annotations

import pathlib

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.config import load_config_and_boot
from ccf.controlplane.temporal_boundary import (
    PinnedTemporalBoundary,
    TemporalBoundaryPolicy,
    TemporalBoundaryUndeclared,
    resolve_temporal_boundary,
    temporal_boundary_policy_key,
)
from ccf.replay.record import PolicyBinding
from tests.deployment.test_config_equivalence import TENANT, _config_document, write_artifact


def _boot(tmp_path: pathlib.Path, document: dict[str, object]) -> object:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = write_artifact(config_dir, "ccf_config.yaml", document)
    return load_config_and_boot(
        path,
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(tmp_path / "namespaced.sqlite3")},
    )


def test_every_derived_key_is_registered_under_the_resolved_tenant(tmp_path: pathlib.Path) -> None:
    booted = _boot(tmp_path, _config_document())
    try:
        assert booted.tenant_id == TENANT
        assert booted.keys is not None
        assert booted.keys.product_class == f"{TENANT}/product_class"
        assert booted.keys.policy_bundle == f"{TENANT}/policy"
        for pin in booted.pins.entries:
            assert pin.key.startswith(f"{TENANT}/"), pin.key
        # and the artifacts really sit under those keys, not the bare ones
        assert booted.keys.product_class in booted.artifacts
        assert "product_class" not in booted.artifacts
    finally:
        booted.handle.close()


def test_a_key_an_author_placed_under_another_prefix_is_confined_to_the_tenant(
    tmp_path: pathlib.Path,
) -> None:
    document = _config_document()
    product_class = dict(document["product_class"])  # type: ignore[arg-type]
    product_class["key"] = "some-other-bank/product_class"
    document["product_class"] = product_class
    booted = _boot(tmp_path, document)
    try:
        assert booted.keys is not None
        assert booted.keys.product_class == f"{TENANT}/some-other-bank/product_class"
        assert "some-other-bank/product_class" not in booted.artifacts
    finally:
        booted.handle.close()


# --- D-IMPL-358 step 5 section A: CFG6, the whole canonical declaration path ---


def test_CFG6_a_declared_temporal_boundary_registers_resolves_and_pins_exactly(
    tmp_path: pathlib.Path,
) -> None:
    """CFG6. The complete path, asserted end to end rather than in pieces.

    ``ccf_config.yaml`` → `DeploymentConfig` → `derive_deployment` → manifest and
    document → `load_config_and_boot` → Control Plane registration →
    `resolve_temporal_boundary` → `PinnedTemporalBoundary` → ``.binding``.

    **The version identity is the point.** The registry derives a version as
    ``content_hash(artifact)``, so asserting ``pinned.version == <the registered
    version>`` alone cannot tell a CARRIED version from one RECOMPUTED from the
    policy — the step-3 measurement. So this asserts three things that together
    pin it: the version the registration actually returned, that the pin equals it,
    and that ``.binding`` is that exact pair. The carried-vs-reconstructed
    distinction itself is proved against an opaque-version plane in
    `tests/controlplane/test_temporal_boundary.py::test_resolving_produces_the_exact_policy_binding_replay_will_carry`;
    this control proves the CONFIG path reaches the same mechanism.
    """
    document = _config_document()
    document["temporal_boundary"] = {
        "max_past_seconds": 86_400,
        "permitted_clock_skew_seconds": 60,
    }
    registry = ControlPlaneRegistry()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    booted = load_config_and_boot(
        write_artifact(config_dir, "ccf_config.yaml", document),
        registry=registry,
        connection={"database_path": str(tmp_path / "cfg6.sqlite3")},
    )

    key = temporal_boundary_policy_key(tenant_id=TENANT)
    assert booted.keys is not None
    assert booted.keys.temporal_boundary == key, "the canonical key did not survive boot"

    # Registered on the Control Plane the boot ran against, at the key the helper
    # fixes — not at a generic section-name key.
    registered_version, artifact = registry.resolve_latest(key)
    assert isinstance(artifact, TemporalBoundaryPolicy)
    assert artifact.max_past_seconds == 86_400
    assert artifact.permitted_clock_skew_seconds == 60

    pinned = resolve_temporal_boundary(registry=registry, tenant_id=TENANT)
    assert isinstance(pinned, PinnedTemporalBoundary)
    assert pinned.key == key
    assert pinned.version == registered_version, (
        "the resolution did not carry the version the registration returned"
    )
    assert pinned.policy == artifact
    assert pinned.binding == PolicyBinding(key=key, version=registered_version)


def test_CFG6_a_config_declaring_no_boundary_boots_and_resolves_undeclared(
    tmp_path: pathlib.Path,
) -> None:
    """The other half: booting succeeds and the resolution says UNDECLARED.

    Absence is not a boot failure — it is a governed condition a later serve
    consumes. Nothing is registered, nothing is invented, and no version exists to
    pin.
    """
    registry = ControlPlaneRegistry()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    booted = load_config_and_boot(
        write_artifact(config_dir, "ccf_config.yaml", _config_document()),
        registry=registry,
        connection={"database_path": str(tmp_path / "cfg6-absent.sqlite3")},
    )
    assert booted.keys is not None
    assert booted.keys.temporal_boundary is None

    undeclared = resolve_temporal_boundary(registry=registry, tenant_id=TENANT)
    assert isinstance(undeclared, TemporalBoundaryUndeclared)
    assert undeclared.key == temporal_boundary_policy_key(tenant_id=TENANT)
    assert undeclared.reason == "temporal-boundary-undeclared"
