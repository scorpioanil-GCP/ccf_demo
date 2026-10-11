# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The public declaration function refuses a reserved ``ccf.`` class id, by name (`D-IMPL-378` K1).

Dave, 2026-10-08 12:29 MST, ruling K1 (b): *"Refuse reserved ccf. names through
the public declaration function; preserve legitimate SDK registration."*

`D-IMPL-84` reserves the ``ccf.`` prefix for the SDK.
``src/ccf/deployment/classes.py::resolve_artifact_class`` — the resolver the
manifest, the single-file config and the paved road share — refuses a ``ccf.``
id that is not a class the SDK ships, because the open envelope
``src/ccf/controlplane/artifacts.py::DeclaredArtifact`` would otherwise
register, pin and enter Decision Replay dimension 2 under an SDK class name with
arbitrary content. The reservation lived only there.
``src/ccf/controlplane/artifacts.py::declared_artifact_class``, the public
function a program calls to build an adopter class over that envelope, applied
none of it. Measured by lane 378d-classid on ``d5d0397d``
(``probe_programmatic_sdk_squat.py``): ``declared_artifact_class(
"ccf.workflow-definition")`` returned an envelope class, and a document stating
that id registered through ``ControlPlaneRegistry.register_typed`` with its key
bound to ``ccf.workflow-definition``.

What is asserted, by mechanism:

1. **The hole as worded.** ``declared_artifact_class`` refuses every ``ccf.``
   id — an SDK class id, an SDK class no manifest addresses, an invented one,
   and the bare prefix — with the refusal named ``ReservedArtifactClassId``,
   carrying the id, before any ``ArtifactClass`` exists. The probe's squat
   registers nothing and audits nothing.
2. **Legitimate SDK registration is preserved.** The reservation is one prefix
   wide and no wider: an adopter's namespace still takes the envelope, parses and
   registers. Every SDK class id still resolves to the SDK's own contract. The
   SDK's own ``ccf.`` classes still register on every config-driven boot path —
   ``load_and_boot``, ``load_config_and_boot`` and the paved road — and the
   declaration function is never handed a ``ccf.`` id on any of them: the SDK
   builds its classes as typed constants and resolves a manifest's SDK ids from
   its reviewed mappings before the envelope is reached, so it needs no
   internal path around the refusal.

The refusal is asserted by its class NAME as a string, not by an import, so a
tree without the guard fails each test on its behavior rather than on an import.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from ccf.authz.capability import Register
from ccf.controlplane.artifacts import (
    ArtifactClass,
    DeclaredArtifact,
    declared_artifact_class,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import classes as class_lookup
from ccf.deployment import load_and_boot, load_config_and_boot
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.deployment.classes import (
    SDK_ARTIFACT_CLASSES,
    SDK_VERSIONED_ARTIFACT_CLASSES,
    resolve_artifact_class,
)
from ccf.products.product import open_product
from ccf.replay.serve import ServedProduct

from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust
from tests.controlplane.capabilities import register_capability
from tests.deployment.conftest import Deployment
from tests.products import paved_fixture as fixture

#: The refusal's class name, asserted by name rather than imported (see the module docstring).
REFUSAL = "ReservedArtifactClassId"

#: The squat the classid lane's probe performed, and the three other shapes the
#: reservation must close: an SDK class id that is manifest-addressable, one that
#: is not (registered by adopter code against its real contract, never through a
#: manifest), an id the SDK does not own at all, and the bare prefix.
RESERVED = ["ccf.workflow-definition", "ccf.hitl-policy", "ccf.made-up-class", "ccf."]

#: Ids in an adopter's own namespace, including two that merely CONTAIN the letters.
ADOPTER = ["acme.policy-bundle", "ccfx.policy-bundle", "notccf.thing", "fixture.ccf.thing"]

SQUAT_KEY = "tenant-x/ccf.workflow-definition/w"


def _envelope(class_id: str) -> dict[str, Any]:
    return {"semver": "1.0.0", "class_id": class_id, "declaration": {"anything": "x"}}


def _assert_named(refusal: BaseException, *, class_id: str) -> None:
    """The guard's own refusal, by name, carrying the id it refused."""
    assert type(refusal).__name__ == REFUSAL, f"{type(refusal).__name__}: {refusal}"
    assert getattr(refusal, "class_id", None) == class_id, refusal
    assert repr(class_id) in str(refusal), f"the refusal does not name {class_id!r}: {refusal}"
    assert "D-IMPL-84" in str(refusal), f"the refusal does not cite the reservation it enforces: {refusal}"
    # `resolve_artifact_class` refuses the same reservation as a ValueError, so a
    # caller that catches ValueError around either door keeps catching it.
    assert isinstance(refusal, ValueError), type(refusal).__mro__


# ---------------------------------------------------------------------------
# 1. THE HOLE AS WORDED.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("class_id", RESERVED)
def test_the_declaration_function_refuses_a_reserved_ccf_id_by_name(class_id: str) -> None:
    """K1 (b): a ``ccf.`` id through the public declaration function is refused, by name."""
    with pytest.raises(ValueError) as raised:
        declared_artifact_class(class_id)
    _assert_named(raised.value, class_id=class_id)


def test_the_programmatic_squat_registers_nothing() -> None:
    """The classid lane's probe, step for step: refused before any class exists, so nothing is filed."""
    registry = ControlPlaneRegistry()
    with pytest.raises(ValueError) as raised:
        squat_class = declared_artifact_class("ccf.workflow-definition")
        artifact = parse_artifact(_envelope("ccf.workflow-definition"), squat_class)
        registry.register_typed(register_capability(SQUAT_KEY, Register), artifact, squat_class)
    _assert_named(raised.value, class_id="ccf.workflow-definition")
    assert registry.versions(SQUAT_KEY) == ()
    assert registry.artifact_class_of(SQUAT_KEY) is None
    assert registry.audit_events() == (), "something was registered or audited before the refusal"


# ---------------------------------------------------------------------------
# 2. Controls: legitimate registration is preserved.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("class_id", ADOPTER)
def test_control_an_adopter_namespace_still_takes_the_envelope_and_registers(class_id: str) -> None:
    """The reservation is one prefix wide and no wider."""
    artifact_class = declared_artifact_class(class_id)
    assert artifact_class.class_id == class_id and artifact_class.contract is DeclaredArtifact
    artifact = parse_artifact(_envelope(class_id), artifact_class)
    registry = ControlPlaneRegistry()
    key = f"tenant-x/{class_id}"
    version = registry.register_typed(register_capability(key, Register), artifact, artifact_class)
    assert registry.resolve(key, version) == artifact
    assert registry.artifact_class_of(key) == class_id


def test_control_every_sdk_class_id_still_resolves_to_its_own_contract() -> None:
    """The resolver every config-driven boot path uses serves the SDK's ids from its reviewed mappings."""
    owned = {**SDK_ARTIFACT_CLASSES, **SDK_VERSIONED_ARTIFACT_CLASSES}
    assert owned, "no SDK class to resolve"
    for class_id, constant in owned.items():
        assert class_id.startswith("ccf."), class_id
        resolved = resolve_artifact_class(class_id)
        assert resolved is constant, class_id
        assert resolved.contract is not DeclaredArtifact, class_id


@pytest.fixture()
def declaration_spy(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """Every id handed to the declaration function, on both names the SDK can reach it by."""
    seen: list[str] = []
    real: Callable[[str], ArtifactClass] = class_lookup.declared_artifact_class

    def spy(class_id: str) -> ArtifactClass:
        seen.append(class_id)
        return real(class_id)

    monkeypatch.setattr(class_lookup, "declared_artifact_class", spy)
    monkeypatch.setattr("ccf.controlplane.artifacts.declared_artifact_class", spy)
    yield seen


def _sdk_pins(pins: Any) -> list[tuple[str, str]]:
    """``(key, class_id)`` for every pin of a class the SDK ships."""
    owned = {**SDK_ARTIFACT_CLASSES, **SDK_VERSIONED_ARTIFACT_CLASSES}
    return [(pin.key, pin.class_id) for pin in pins.entries if pin.class_id in owned]


def test_control_the_manifest_boot_registers_the_sdks_own_classes(
    deployment: Deployment, tmp_path: pathlib.Path, declaration_spy: list[str]
) -> None:
    """``load_and_boot``: every SDK class registers under its own id; the declaration function sees adopters only."""
    registry = ControlPlaneRegistry()
    booted = load_and_boot(
        deployment.manifest_path, registry=registry, connection={"database_path": str(tmp_path / "graph.sqlite3")}
    )
    try:
        registered = _sdk_pins(booted.pins)
        assert len(registered) >= 5, registered
        for key, class_id in registered:
            assert registry.artifact_class_of(key) == class_id, (key, class_id)
    finally:
        booted.handle.close()
    assert declaration_spy, "the fixture's adopter class never reached the declaration function"
    assert not [seen for seen in declaration_spy if seen.startswith("ccf.")], declaration_spy


def test_control_the_config_boot_and_the_paved_road_register_the_sdks_own_classes(
    tmp_path: pathlib.Path, declaration_spy: list[str]
) -> None:
    """``open_product`` serves, and ``load_config_and_boot`` pins the SDK's classes, over one paved tree."""
    root = fixture.write_tree(
        tmp_path / "deployment",
        config=fixture.producer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER),
        environment=fixture.producer_environment_text(),
    )
    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(control_plane, tenant_id=fixture.PRODUCER_TENANT)
    environ = {fixture.CHILD_DSN_VAR: "postgresql://fixture"}
    with open_product(
        erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
        config_root=root,
        scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ=environ,
        control_plane=control_plane,
        clock=lambda: fixture.ADMITTED_AT,
    ) as opened:
        served = opened.answer(
            opened.question(
                subject="acct-1",
                asked_at=fixture.ASKED_AT,
                intent="fixture-intent",
                freshness="fixture-freshness",
                parameters={fixture.THRESHOLD_PARAMETER: 1000},
            )
        )
        assert isinstance(served, ServedProduct), served
        fabric = load_config_and_boot(
            opened.config_path,
            registry=control_plane,
            connection={"database_path": str(tmp_path / "config-boot.sqlite3")},
            for_question=True,
        )
        try:
            registered = _sdk_pins(fabric.pins)
            assert len(registered) >= 3, registered
            for key, class_id in registered:
                assert control_plane.artifact_class_of(key) == class_id, (key, class_id)
        finally:
            fabric.handle.close()
    assert not [seen for seen in declaration_spy if seen.startswith("ccf.")], declaration_spy
