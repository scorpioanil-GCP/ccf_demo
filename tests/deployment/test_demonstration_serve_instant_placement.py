# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A demonstration serve instant the composition would silently never read is refused (`D-IMPL-378` C1).

**SDK-defined** (CLAUDE.md §11). Lane ``378d-democlock`` residual (e) and the
sweep the coordinator authorized after it. The composition reads ONE key,
``{tenant}/ccf.demonstration-serve-instant``
(`ccf.controlplane.demonstration_serve_instant.demonstration_serve_instant_key`),
and reads it once, at composition. Measured at ``67f10e84`` (lane file
``probe-inert-paths-67f10e8.txt``), five declarations booted cleanly and were
never honored — the deployment served on its real clock, or on another
declaration, with nothing saying so:

* P1 — a manifest entry at another key (``demo-instant``);
* P2 — a manifest entry written under another tenant, which key placement
  confines to ``{tenant}/other-tenant/…`` rather than refusing;
* P3a — two entries, one of them misplaced;
* P3b — two entries whose keys place to ONE key, the first instant silently
  replaced by the second;
* P8 — a second version registered on the Control Plane before composition,
  the latest silently winning over the manifest's declaration.

Every one is now refused by name, before anything is registered, or at
composition:

* P1, P2, P3a by this class's own rule — every declaration must sit at the
  derived key — in `ccf.deployment.manifest.register_manifest_entries`, the one
  loop both boot doors and the paved road run, and which a composition root may
  call directly (the direct-call test below);
* P3b by the rule for EVERY class: two entries whose keys place to one key are
  refused by `ccf.deployment.manifest.manifest_under_tenant`
  (``ManifestKeysPlaceToOneKey``, lane ``378d-placement``) before the loop is
  reached. With that rule and the manifest contract's own key-uniqueness check,
  two declarations at ONE key cannot reach the loop at all (both shown below), so
  this class's rule carries no branch for that case;
* P8 at composition, in `ccf.products.demonstration_clock.compose_serve_clock`.

**The config door cannot misplace one at all**, and two tests here keep that
true: the `demonstration_serve_instant:` section derives its key and refuses a
stated ``key``, and every other section's derivation injects ``semver``, which
the contract refuses at parse.
"""

from __future__ import annotations

import pathlib
import shutil
from typing import Any

import pytest
import yaml

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.deployment.config import load_config_and_boot

from tests.deployment.conftest import TENANT, Deployment, manifest_document, write_artifact

#: The SDK's class id for the declaration, spelled once here.
CLASS_ID = "ccf.demonstration-serve-instant"

#: Where the composition reads the fixture tenant's declaration.
DERIVED = f"{TENANT}/{CLASS_ID}"

#: Two different declared instants.
FIRST = "2026-03-02T12:05:00+00:00"
SECOND = "2026-03-02T12:07:00+00:00"

#: The client suite's committed config-form fixture, for the config door.
CONFIG_FIXTURE = pathlib.Path(__file__).resolve().parents[1] / "client" / "fixtures" / "deployment"

#: The refusal's class name, asserted by name rather than imported, so a tree
#: without the guard fails each test on its BEHAVIOR (nothing raised) instead of
#: on an import.
REFUSAL = "DemonstrationServeInstantMisplaced"


def _manifest(deployment: Deployment, declarations: list[tuple[str, str]], *, name: str) -> pathlib.Path:
    """The fixture manifest plus one demonstration entry per ``(authored key, instant)``."""
    body = manifest_document()
    for index, (key, instant) in enumerate(declarations):
        filename = f"demonstration-{index}.yaml"
        write_artifact(deployment.root, filename, {"serve_instant": instant})
        body["artifacts"] = [
            *body["artifacts"],
            {
                "path": filename,
                "key": key,
                "class_id": CLASS_ID,
                "role": "register",
                "registration": "typed",
            },
        ]
    return deployment.variant_manifest(name, body)


def _refused_at_boot(manifest: pathlib.Path, tmp_path: pathlib.Path) -> tuple[ValueError, ControlPlaneRegistry]:
    """Boot ``manifest``; return the refusal and the Control Plane it left."""
    registry = ControlPlaneRegistry()
    with pytest.raises(ValueError) as raised:
        load_and_boot(
            manifest,
            registry=registry,
            connection={"database_path": str(tmp_path / "graph.sqlite3")},
        )
    return raised.value, registry


def _assert_refused(refusal: ValueError, registry: ControlPlaneRegistry, *, reason: str, keys: tuple[str, ...]) -> None:
    """The guard's own refusal, its stated reason and keys, and nothing registered."""
    assert type(refusal).__name__ == REFUSAL, f"{type(refusal).__name__}: {refusal}"
    assert getattr(refusal, "reason", None) == reason, refusal
    assert getattr(refusal, "keys", None) == keys, refusal
    assert getattr(refusal, "expected", None) == DERIVED, refusal
    assert registry.audit_events() == (), "something was registered before the refusal"


# ---------------------------------------------------------------------------
# The manifest door: P1, P2, P3a, P3b.
# ---------------------------------------------------------------------------


def test_p1_a_declaration_at_another_key_is_refused_at_boot(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    refusal, registry = _refused_at_boot(
        _manifest(deployment, [("demo-instant", FIRST)], name="p1.yaml"), tmp_path
    )
    _assert_refused(refusal, registry, reason="misplaced-key", keys=(f"{TENANT}/demo-instant",))


def test_p2_a_declaration_written_under_another_tenant_is_refused_at_boot(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    refusal, registry = _refused_at_boot(
        _manifest(deployment, [(f"other-tenant/{CLASS_ID}", FIRST)], name="p2.yaml"), tmp_path
    )
    _assert_refused(
        refusal, registry, reason="misplaced-key", keys=(f"{TENANT}/other-tenant/{CLASS_ID}",)
    )


def test_p3a_two_declarations_one_misplaced_are_refused_at_boot(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The misplaced one of two is refused, by the same rule as P1: it is not where the composition reads."""
    refusal, registry = _refused_at_boot(
        _manifest(deployment, [(CLASS_ID, FIRST), ("demo-instant", SECOND)], name="p3a.yaml"),
        tmp_path,
    )
    _assert_refused(refusal, registry, reason="misplaced-key", keys=(f"{TENANT}/demo-instant",))


def test_p3b_two_declarations_placing_to_one_key_meet_the_rule_for_every_class(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """`ManifestKeysPlaceToOneKey` (lane ``378d-placement``) refuses P3b before this class's rule is reached.

    One rule for every class is the right layer: the same two entries of ANY
    class would otherwise keep one document and drop the other.
    """
    refusal, registry = _refused_at_boot(
        _manifest(deployment, [(CLASS_ID, FIRST), (DERIVED, SECOND)], name="p3b.yaml"), tmp_path
    )
    assert type(refusal).__name__ == "ManifestKeysPlaceToOneKey", f"{type(refusal).__name__}: {refusal}"
    assert getattr(refusal, "authored_keys", None) == (CLASS_ID, DERIVED), refusal
    assert getattr(refusal, "placed_key", None) == DERIVED, refusal
    assert registry.audit_events() == (), "something was registered before the refusal"


def test_a_direct_register_loop_call_lands_on_the_misplaced_rule(tmp_path: pathlib.Path) -> None:
    """A composition root calling the loop directly, without placing keys, still cannot pass two declarations.

    Some composition roots call `register_manifest_entries` themselves (the paved
    road's consumer chain, cp-20's deployment). Bypassing `manifest_under_tenant`,
    the two P3b entries arrive as two DIFFERENT keys — one bare, one under the
    tenant — so the bare one is refused as misplaced before anything is
    registered. This is why the class's rule needs no branch for two
    declarations at one key: that case is unreachable on this route too.
    """
    from ccf.controlplane.artifacts import DeploymentManifest
    from ccf.controlplane.demonstration_serve_instant import DemonstrationServeInstant
    from ccf.deployment.manifest import register_manifest_entries

    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        *(
            {"path": f"demonstration-{index}.yaml", "key": key, "class_id": CLASS_ID,
             "role": "register", "registration": "typed"}
            for index, key in enumerate((DERIVED, CLASS_ID))
        ),
    ]
    manifest = DeploymentManifest.model_validate(body)
    parsed = {
        DERIVED: DemonstrationServeInstant.model_validate({"serve_instant": FIRST}),
        CLASS_ID: DemonstrationServeInstant.model_validate({"serve_instant": SECOND}),
    }
    registry = ControlPlaneRegistry()
    with pytest.raises(ValueError) as raised:
        register_manifest_entries(
            manifest, parsed, registry=registry, tenant=TENANT, only=frozenset(parsed)
        )
    _assert_refused(raised.value, registry, reason="misplaced-key", keys=(CLASS_ID,))


def test_two_entries_at_one_key_never_reach_the_register_loop() -> None:
    """The manifest contract refuses a key declared twice — the last way two declarations could share one key."""
    from ccf.controlplane.artifacts import DeploymentManifest

    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        *(
            {"path": f"demonstration-{index}.yaml", "key": DERIVED, "class_id": CLASS_ID,
             "role": "register", "registration": "typed"}
            for index in range(2)
        ),
    ]
    with pytest.raises(ValueError, match="is declared twice"):
        DeploymentManifest.model_validate(body)


def test_control_one_declaration_at_the_derived_key_boots(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Control: the one correct form boots and lands where the composition reads it."""
    registry = ControlPlaneRegistry()
    booted = load_and_boot(
        _manifest(deployment, [(CLASS_ID, FIRST)], name="control.yaml"),
        registry=registry,
        connection={"database_path": str(tmp_path / "graph.sqlite3")},
    )
    try:
        assert len(registry.versions(DERIVED)) == 1
    finally:
        booted.handle.close()


# ---------------------------------------------------------------------------
# The composition: P8.
# ---------------------------------------------------------------------------


def test_p8_a_second_version_on_the_control_plane_is_refused_at_composition(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The manifest's declaration and a programmatic one: the latest must not silently win."""
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.artifacts.protocol import WriteKinds
    from ccf.controlplane.demonstration_serve_instant import (
        DEMONSTRATION_SERVE_INSTANT,
        DemonstrationServeInstant,
    )
    from ccf.products.demonstration_clock import compose_serve_clock
    from ccf.products.resolver import _utc_now

    from tests.composition import register_typed_at_composition

    registry = ControlPlaneRegistry()
    booted = load_and_boot(
        _manifest(deployment, [(CLASS_ID, FIRST)], name="p8.yaml"),
        registry=registry,
        connection={"database_path": str(tmp_path / "graph.sqlite3")},
    )
    try:
        register_typed_at_composition(
            registry,
            DERIVED,
            DemonstrationServeInstant(serve_instant=SECOND),
            DEMONSTRATION_SERVE_INSTANT,
        )
        assert len(registry.versions(DERIVED)) == 2
        with pytest.raises(ValueError) as raised:
            compose_serve_clock(
                control_plane=registry,
                fabric=booted,
                artifact_store=FileArtifactStore(
                    root=tmp_path / "store", write_kinds=WriteKinds.declare({})
                ),
                admission_clock=_utc_now,
                sdk_clock=_utc_now,
            )
        refusal = raised.value
        assert type(refusal).__name__ == REFUSAL, f"{type(refusal).__name__}: {refusal}"
        assert getattr(refusal, "reason", None) == "several-declarations", refusal
        assert getattr(refusal, "keys", None) == (DERIVED, DERIVED), refusal
    finally:
        booted.handle.close()


# ---------------------------------------------------------------------------
# The config door cannot misplace a declaration: pinned so it stays true.
# ---------------------------------------------------------------------------


def _config_copy(tmp_path: pathlib.Path, mutate: Any) -> pathlib.Path:
    root = tmp_path / "deployment"
    shutil.copytree(CONFIG_FIXTURE, root)
    config = root / "ccf_config.yaml"
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
    mutate(document)
    config.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return config


def test_the_config_section_registers_at_the_derived_key(tmp_path: pathlib.Path) -> None:
    config = _config_copy(
        tmp_path, lambda document: document.update({"demonstration_serve_instant": {"serve_instant": FIRST}})
    )
    tenant = yaml.safe_load(config.read_text(encoding="utf-8"))["tenant_id"]
    registry = ControlPlaneRegistry()
    booted = load_config_and_boot(
        config, registry=registry, connection={"database_path": str(tmp_path / "graph.sqlite3")}
    )
    try:
        assert len(registry.versions(f"{tenant}/{CLASS_ID}")) == 1
    finally:
        booted.handle.close()


def test_the_config_section_refuses_a_stated_key(tmp_path: pathlib.Path) -> None:
    config = _config_copy(
        tmp_path,
        lambda document: document.update(
            {"demonstration_serve_instant": {"serve_instant": FIRST, "key": "demo-instant"}}
        ),
    )
    with pytest.raises(ValueError, match="`demonstration_serve_instant:` section states 'key'"):
        load_config_and_boot(
            config, registry=ControlPlaneRegistry(), connection={"database_path": str(tmp_path / "g.sqlite3")}
        )


def test_no_other_config_section_can_carry_the_class(tmp_path: pathlib.Path) -> None:
    """An adopter-owned section overriding its class id gets `semver` injected, which the contract refuses."""
    from ccf.controlplane.artifacts import ArtifactLoadError

    def override(document: dict[str, Any]) -> None:
        document["request_contract"] = {
            "class_id": CLASS_ID,
            "role": "register",
            "registration": "typed",
            "serve_instant": FIRST,
        }

    config = _config_copy(tmp_path, override)
    with pytest.raises(ArtifactLoadError, match=f"not a valid {CLASS_ID}"):
        load_config_and_boot(
            config, registry=ControlPlaneRegistry(), connection={"database_path": str(tmp_path / "g.sqlite3")}
        )
