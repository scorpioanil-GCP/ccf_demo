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
