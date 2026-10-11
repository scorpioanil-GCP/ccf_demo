# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The manifest door refuses a document that states a class other than its entry's, by name, before anything is registered.

`D-IMPL-378`, lane 378d-classid (CLAUDE.md §9: the three-issue cap, lightweight
remediation). A manifest entry names the class its document is validated as;
an open-envelope document
(``src/ccf/controlplane/artifacts.py::DeclaredArtifact``) also states its class
in its own ``class_id``. Measured on ``a15f92ee``, with the fixture
deployment's policy bundle rewritten to state ``fixture.other-bundle`` under an
entry naming ``fixture.policy-bundle``: ``load_and_boot`` BOOTED. It registered
and pinned the document as ``fixture.policy-bundle`` — the registry bound the
key to that class and the pin recorded it, which is what Decision Replay
dimension 2 carries — while ``BootedFabric.artifacts`` handed back a document
saying it is ``fixture.other-bundle``. A ``role: load`` entry was handed back
the same way.

The refusal is asserted by its own class NAME and attributes, against a Control
Plane that recorded nothing and a fabric that was never booted. The name is a
string rather than an import so that a tree without the guard fails each test
on its behavior, not on an import. The control holds that the fixture
deployment, whose documents state the classes their entries name, still boots.
"""

from __future__ import annotations

import pathlib

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot

from tests.deployment.conftest import (
    ARTIFACT_SET,
    POLICY_BUNDLE_KEY,
    TENANT,
    Deployment,
    write_artifact,
)

#: The refusal's class name, asserted by name rather than imported (see the module docstring).
REFUSAL = "ArtifactClassIdMismatch"

#: The class the fixture manifest names for its policy bundle, and the class the rewritten document states.
PRESENTED = "fixture.policy-bundle"
STATES = "fixture.other-bundle"


def _policy_document() -> dict[str, object]:
    return dict(next(doc for key, _f, _c, _r, _g, doc in ARTIFACT_SET if key == POLICY_BUNDLE_KEY))


def _boot(manifest: pathlib.Path, tmp_path: pathlib.Path, registry: ControlPlaneRegistry) -> object:
    return load_and_boot(manifest, registry=registry, connection={"database_path": str(tmp_path / "graph.sqlite3")})


def _assert_refused_before_anything(
    refusal: BaseException, registry: ControlPlaneRegistry, tmp_path: pathlib.Path, *, presented: str
) -> None:
    assert type(refusal).__name__ == REFUSAL, f"{type(refusal).__name__}: {refusal}"
    assert getattr(refusal, "presented_class_id", None) == presented, refusal
    assert getattr(refusal, "document_class_id", None) == STATES, refusal
    # Every other boot refusal is a ValueError; a caller that catches ValueError around a boot keeps catching this one.
    assert isinstance(refusal, ValueError), type(refusal).__mro__
    assert registry.audit_events() == (), "something was minted or registered before the refusal"
    assert not (tmp_path / "graph.sqlite3").exists(), "the fabric was booted before the refusal"


def test_a_register_entry_whose_document_states_another_class_is_refused_at_boot(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """THE HOLE AS WORDED: the policy bundle's entry names one class and its document states another."""
    document = _policy_document()
    document["class_id"] = STATES
    filename = next(f for key, f, _c, _r, _g, _d in ARTIFACT_SET if key == POLICY_BUNDLE_KEY)
    write_artifact(deployment.root, filename, document)
    registry = ControlPlaneRegistry()
    with pytest.raises((ValueError, TypeError)) as raised:
        _boot(deployment.manifest_path, tmp_path, registry)
    _assert_refused_before_anything(raised.value, registry, tmp_path, presented=PRESENTED)


def test_a_load_entry_whose_document_states_another_class_is_refused_at_boot(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """A ``role: load`` entry is parsed as its class too, and handed back on the boot result under it."""
    document = _policy_document()
    document["class_id"] = STATES
    write_artifact(deployment.root, "extra-bundle.yaml", document)
    body = dict(deployment.manifest_document)
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": "extra-bundle.yaml",
            "key": f"{TENANT}/extra-bundle",
            "class_id": "fixture.extra-bundle",
            "role": "load",
            "registration": "typed",
        },
    ]
    manifest = deployment.variant_manifest("manifest-with-load.yaml", body)
    registry = ControlPlaneRegistry()
    with pytest.raises((ValueError, TypeError)) as raised:
        _boot(manifest, tmp_path, registry)
    _assert_refused_before_anything(raised.value, registry, tmp_path, presented="fixture.extra-bundle")


def test_control_the_fixture_deployment_whose_documents_state_their_entries_classes_boots(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    registry = ControlPlaneRegistry()
    booted = load_and_boot(
        deployment.manifest_path, registry=registry, connection={"database_path": str(tmp_path / "graph.sqlite3")}
    )
    try:
        pin = next(p for p in booted.pins.entries if p.key == POLICY_BUNDLE_KEY)
        artifact = booted.artifacts[POLICY_BUNDLE_KEY]
        assert pin.class_id == PRESENTED == getattr(artifact, "class_id", None)
        assert registry.artifact_class_of(POLICY_BUNDLE_KEY) == PRESENTED
    finally:
        booted.handle.close()
