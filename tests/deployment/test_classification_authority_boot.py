"""SEC-023 — a deployment whose Policy operator reads a source-asserted attribute refuses to boot.

Security row SEC-023 under `D-IMPL-372` (and `D-IMPL-368..371`), ruling Q15 (a),
with Dave's correction of 2026-10-06: *completion requires fail-closed
enforcement wherever classification controls access; updating examples alone
does not establish that guarantee.*

The repair at L2 (``src/ccf/assembly/worker.py::EntityResolutionRule.attribute_authorities``)
only governs an attribute a deployment DECLARES. This module holds the
construction-time half: where the resolution spec and the Policy operator's
parameters are both known — ``src/ccf/deployment/manifest.py::_register_and_boot``,
the spine both paved doors share — a ``classification_attribute_by_class`` entry
that names an attribute a resolution rule writes with no authority declaration
refuses the boot by name, before anything is registered.
"""

from __future__ import annotations

import copy
import pathlib
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from tests.deployment.conftest import (
    ARTIFACT_SET,
    POLICY_PARAMS_KEY,
    RESOLUTION_SPEC_KEY,
    Deployment,
    write_artifact,
)


def _resolution_document() -> tuple[str, dict[str, Any]]:
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        if key == RESOLUTION_SPEC_KEY:
            return filename, copy.deepcopy(document)
    raise AssertionError("the fixture declares no resolution spec")


def _boot(deployment: Deployment, tmp_path: pathlib.Path, name: str) -> Any:
    return load_and_boot(
        deployment.manifest_path,
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(tmp_path / name)},
    )


def test_the_fixture_deployment_declares_authority_and_boots(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The paved path: the fixture names who may assert ``classification``, and boots."""
    _filename, document = _resolution_document()
    governed = [
        rule for rule in document["entity_rules"] if rule.get("attribute_authorities")
    ]
    assert governed, "the fixture's resolution spec must declare an authority"
    booted = _boot(deployment, tmp_path, "declared.sqlite")
    booted.handle.close()


def test_an_ungoverned_classification_attribute_refuses_the_boot_by_name(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Remove the declaration: the Policy operator now reads a source-asserted label."""
    from ccf.deployment.manifest import UngovernedClassificationAttribute

    filename, document = _resolution_document()
    for rule in document["entity_rules"]:
        rule.pop("attribute_authorities", None)
    write_artifact(deployment.root, filename, document)

    with pytest.raises(UngovernedClassificationAttribute) as refused:
        _boot(deployment, tmp_path, "ungoverned.sqlite")
    assert refused.value.attribute == "classification"
    assert refused.value.entity_class == "account"
    assert refused.value.operator_key.endswith(POLICY_PARAMS_KEY)
    assert "UngovernedClassificationAttribute" in str(refused.value)
