"""Two manifest entries whose keys PLACE to one Control Plane key are refused at boot, by name.

`D-IMPL-378`, lane 378d-placement (CLAUDE.md §9: the three-issue cap, lightweight
remediation). Key placement (`D-IMPL-354`,
``src/ccf/deployment/manifest.py::manifest_under_tenant``) maps a bare key ``k``
and the full-grammar ``{tenant}/k`` to ONE string. Measured before the guard
existed, through both boot doors:

* **Same class** — the deployment BOOTS. Placement re-keys the parsed documents
  into a mapping that keeps one document per placed key (the later one in
  manifest order), and the register loop registers that survivor under both
  entries. The other document is never registered, never pinned and absent from
  ``BootedFabric.artifacts``, and nothing says so.
* **Across classes** — the survivor is registered under the EARLIER entry's
  class, and an unrelated ``TypeError`` stops the boot only after earlier
  entries were registered. With two adopter-owned bundle classes, the policy
  bundle on the Control Plane was by then the other bundle's document.
* **A** ``role: load`` **entry ahead of a** ``register`` **one** — the
  deployment BOOTS and the ``load`` document is gone from
  ``BootedFabric.artifacts``.

``DeploymentManifest._keys_are_unique`` sees none of it: it compares the keys as
AUTHORED, and the tenant is often known only when the caller supplies it.

Every refusal here is asserted by the refusal's own class NAME and its own
attributes, and against a Control Plane that recorded nothing: a guard that fires
after the first mint, or a different guard refusing for another reason, fails
these tests. The name is a string rather than an import so that a tree without
the guard fails each test on its behavior, not on an import.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Callable
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DEPLOYMENT_MANIFEST, DeploymentManifest, load_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_and_boot, load_config_and_boot
from ccf.deployment.manifest import manifest_under_tenant

from tests.deployment.conftest import (
    ARTIFACT_SET,
    HALF_LIFE_KEY,
    PERSPECTIVE_KEY,
    POLICY_BUNDLE_KEY,
    SIGNAL_BATCH_KEY,
    TENANT,
    Deployment,
    manifest_document,
    write_artifact,
)

#: The refusal's class name, asserted by name rather than imported (see the module docstring).
REFUSAL = "ManifestKeysPlaceToOneKey"

#: The fixture manifest's half-life entry, authored in the full grammar.
BARE_HALF_LIFE_KEY = HALF_LIFE_KEY.removeprefix(f"{TENANT}/")


def _document(class_id: str) -> dict[str, Any]:
    """A deep copy of the fixture document of ``class_id``."""
    return copy.deepcopy(next(doc for _k, _f, cid, _r, _g, doc in ARTIFACT_SET if cid == class_id))


def _entry(body: dict[str, Any], class_id: str) -> dict[str, Any]:
    """The fixture manifest's (first) entry of ``class_id``."""
    return next(entry for entry in body["artifacts"] if entry["class_id"] == class_id)


def _second_half_life(deployment: Deployment) -> str:
    """Write a second, different half-life table beside the fixture's; return its filename."""
    document = _document("ccf.half-life-table")
    document["entries"]["fixture-observation"]["half_life_seconds"] = 7
    write_artifact(deployment.root, "half-life-second.yaml", document)
    return "half-life-second.yaml"


def _boot_manifest(manifest: pathlib.Path, tmp_path: pathlib.Path) -> Callable[[ControlPlaneRegistry], BootedFabric]:
    def boot(registry: ControlPlaneRegistry) -> BootedFabric:
        return load_and_boot(
            manifest, registry=registry, connection={"database_path": str(tmp_path / "graph.sqlite3")}
        )

    return boot


def _refused(boot: Callable[[ControlPlaneRegistry], BootedFabric]) -> tuple[BaseException, ControlPlaneRegistry]:
    """Boot; return what refused it and the Control Plane it left.

    ``TypeError`` is admitted beside ``ValueError`` only so that the late,
    unrelated refusal the cross-class cases met before the guard existed reaches
    the name assertion in :func:`_assert_refused` and is reported there.
    """
    registry = ControlPlaneRegistry()
    with pytest.raises((ValueError, TypeError)) as raised:
        boot(registry)
    return raised.value, registry


def _assert_named(
    refusal: BaseException, *, authored: tuple[str, str], placed: str, tenant: str = TENANT
) -> None:
    """The guard's own refusal, by name: both authored keys, in manifest order, and the placed key."""
    assert type(refusal).__name__ == REFUSAL, f"{type(refusal).__name__}: {refusal}"
    # Every other boot refusal in this module is a ValueError; a caller that
    # catches ValueError around a boot keeps catching this one.
    assert isinstance(refusal, ValueError), type(refusal).__mro__
    assert getattr(refusal, "authored_keys", None) == authored, refusal
    assert getattr(refusal, "placed_key", None) == placed, refusal
    assert getattr(refusal, "tenant", None) == tenant, refusal
    for key in (*authored, placed):
        assert repr(key) in str(refusal), f"the refusal does not name {key!r}: {refusal}"


def _assert_refused(
    refusal: BaseException,
    registry: ControlPlaneRegistry,
    *,
    authored: tuple[str, str],
    placed: str,
) -> None:
    """:func:`_assert_named`, against a Control Plane that recorded nothing — no mint, no registration."""
    _assert_named(refusal, authored=authored, placed=placed)
    assert registry.audit_events() == (), "something was minted or registered before the refusal"


# ---------------------------------------------------------------------------
# The manifest door.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bare_first", [False, True], ids=["full-grammar-key-first", "bare-key-first"])
def test_two_entries_of_one_class_placing_to_one_key_are_refused_at_boot(
    deployment: Deployment, tmp_path: pathlib.Path, bare_first: bool
) -> None:
    """The measured hole: two half-life tables, one key once placed — only the second was in force."""
    body = manifest_document()
    half_life = _entry(body, "ccf.half-life-table")
    first_key, second_key = (BARE_HALF_LIFE_KEY, HALF_LIFE_KEY) if bare_first else (HALF_LIFE_KEY, BARE_HALF_LIFE_KEY)
    half_life["key"] = first_key
    body["artifacts"].append({**half_life, "key": second_key, "path": _second_half_life(deployment)})
    manifest = deployment.variant_manifest("same-class.yaml", body)

    refusal, registry = _refused(_boot_manifest(manifest, tmp_path))

    _assert_refused(refusal, registry, authored=(first_key, second_key), placed=HALF_LIFE_KEY)


def test_two_adopter_classes_placing_to_one_key_are_refused_before_anything_is_registered(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Across classes: before the guard, the other bundle's document was registered as the policy bundle."""
    body = manifest_document()
    other = {
        "semver": "1.0.0",
        "class_id": "fixture.other-bundle",
        "declaration": {"permitted_classifications": ["fixture-closed"]},
    }
    write_artifact(deployment.root, "other-bundle.yaml", other)
    bare = POLICY_BUNDLE_KEY.removeprefix(f"{TENANT}/")
    body["artifacts"].append(
        {**_entry(body, "fixture.policy-bundle"), "key": bare, "class_id": "fixture.other-bundle", "path": "other-bundle.yaml"}
    )
    manifest = deployment.variant_manifest("cross-class.yaml", body)

    refusal, registry = _refused(_boot_manifest(manifest, tmp_path))

    _assert_refused(refusal, registry, authored=(POLICY_BUNDLE_KEY, bare), placed=POLICY_BUNDLE_KEY)


def test_a_load_entry_placing_onto_a_register_entry_is_refused_at_boot(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Across roles: before the guard, the deployment booted and the ``load`` document was gone."""
    body = manifest_document()
    batch = _entry(body, "ccf.signal-batch")
    body["artifacts"].remove(batch)
    bare = PERSPECTIVE_KEY.removeprefix(f"{TENANT}/")
    body["artifacts"].insert(0, {**batch, "key": bare})
    manifest = deployment.variant_manifest("cross-role.yaml", body)

    refusal, registry = _refused(_boot_manifest(manifest, tmp_path))

    _assert_refused(refusal, registry, authored=(bare, PERSPECTIVE_KEY), placed=PERSPECTIVE_KEY)


def test_control_two_entries_at_distinct_placed_keys_both_boot_and_both_register(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The control: a bare key that places beside, not onto, another entry boots, and both documents are in force."""
    body = manifest_document()
    second_key = f"{BARE_HALF_LIFE_KEY}-second"
    body["artifacts"].append(
        {**_entry(body, "ccf.half-life-table"), "key": second_key, "path": _second_half_life(deployment)}
    )
    manifest = deployment.variant_manifest("distinct.yaml", body)
    registry = ControlPlaneRegistry()

    booted = _boot_manifest(manifest, tmp_path)(registry)

    try:
        placed_second = f"{TENANT}/{second_key}"
        first_document = booted.artifacts[HALF_LIFE_KEY]
        second_document = booted.artifacts[placed_second]
        assert getattr(first_document, "entries")["fixture-observation"].half_life_seconds == 3600
        assert getattr(second_document, "entries")["fixture-observation"].half_life_seconds == 7
        assert registry.versions(HALF_LIFE_KEY) == (content_hash(first_document),)
        assert registry.versions(placed_second) == (content_hash(second_document),)
        assert booted.pins.version_for(HALF_LIFE_KEY) == content_hash(first_document)
        assert booted.pins.version_for(placed_second) == content_hash(second_document)
        assert SIGNAL_BATCH_KEY in booted.artifacts
    finally:
        booted.handle.close()


# ---------------------------------------------------------------------------
# The single-file config door (`load_config_and_boot`), through the same placement.
# ---------------------------------------------------------------------------

CONFIG_TENANT = TENANT


def _config_document(**operators: dict[str, Any]) -> dict[str, Any]:
    """A minimal single-file deployment declaring ``operators`` (test-side values, CINV-01)."""
    return {
        "semver": "1.0.0",
        "tenant_id": CONFIG_TENANT,
        "backend": "sqlite",
        "product_class": {
            "schema_name": "fixture.placement-product",
            "schema_version": "1.0.0",
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": "fixture/placement-product/max-ttl",
            "required_operator_keys": sorted(operators),
        },
        "operators": operators,
        "resolution": {
            "entity_rules": [
                {
                    "match_key": "widget_ref",
                    "entity_class": "widget",
                    "identity_keys": ["widget_ref"],
                    "attribute_keys": ["label"],
                }
            ]
        },
        "half_life": {
            "widget": {
                "half_life_seconds": 3600,
                "decay_driver": "fixture",
                "supersession_event": "fixture-superseded",
            }
        },
        "policy": {
            "class_id": "fixture.placement-policy-bundle",
            "role": "register",
            "registration": "typed",
            "regime": "fixture-regime",
        },
        "default_perspective": {"principal_id": "fixture-principal", "role": "analyst"},
    }


def _boot_config(document: dict[str, Any], tmp_path: pathlib.Path) -> Callable[[ControlPlaneRegistry], BootedFabric]:
    config = write_artifact(tmp_path, "ccf_config.yaml", document)

    def boot(registry: ControlPlaneRegistry) -> BootedFabric:
        return load_config_and_boot(
            config, registry=registry, connection={"database_path": str(tmp_path / "graph.sqlite3")}
        )

    return boot


def test_the_config_door_refuses_two_operator_entries_placing_to_one_key(tmp_path: pathlib.Path) -> None:
    """Same class through the single-file door: before the guard, ``require_valid_at_boundary: true`` was dropped."""
    placed = f"{CONFIG_TENANT}/temporal.as-of-boundary"
    document = _config_document(
        **{
            "temporal.as-of-boundary": {"require_valid_at_boundary": True},
            "temporal.second": {"key": placed, "require_valid_at_boundary": False},
        }
    )

    refusal, registry = _refused(_boot_config(document, tmp_path))

    _assert_refused(refusal, registry, authored=("temporal.as-of-boundary", placed), placed=placed)


def test_the_config_door_refuses_a_section_key_placing_onto_another_section(tmp_path: pathlib.Path) -> None:
    """Across classes through the single-file door: ``half_life`` keyed onto the ``policy`` section's placed key."""
    placed = f"{CONFIG_TENANT}/policy"
    document = _config_document(**{"temporal.as-of-boundary": {"require_valid_at_boundary": True}})
    document["half_life"] = {"key": placed, **document["half_life"]}

    refusal, registry = _refused(_boot_config(document, tmp_path))

    _assert_refused(refusal, registry, authored=(placed, "policy"), placed=placed)


def test_control_the_config_door_boots_a_key_override_that_places_beside_the_others(tmp_path: pathlib.Path) -> None:
    """The config-door control: a ``key:`` override at a distinct placed key boots and both operators register."""
    document = _config_document(
        **{
            "temporal.as-of-boundary": {"require_valid_at_boundary": True},
            "temporal.second": {"key": "temporal.second-parameters", "require_valid_at_boundary": False},
        }
    )
    registry = ControlPlaneRegistry()

    booted = _boot_config(document, tmp_path)(registry)

    try:
        first = booted.artifacts[f"{CONFIG_TENANT}/temporal.as-of-boundary"]
        second = booted.artifacts[f"{CONFIG_TENANT}/temporal.second-parameters"]
        assert getattr(first, "require_valid_at_boundary") is True
        assert getattr(second, "require_valid_at_boundary") is False
        assert registry.versions(f"{CONFIG_TENANT}/temporal.as-of-boundary") == (content_hash(first),)
        assert registry.versions(f"{CONFIG_TENANT}/temporal.second-parameters") == (content_hash(second),)
    finally:
        booted.handle.close()


# ---------------------------------------------------------------------------
# The placement step itself: what `open_product`'s consumer chain and every
# direct caller run before `register_manifest_entries`.
# ---------------------------------------------------------------------------


def test_placement_itself_refuses_two_entries_placing_to_one_key_whatever_parsed_holds() -> None:
    """``manifest_under_tenant`` reads the manifest's entries, not the (possibly partial) parsed mapping."""
    body = manifest_document()
    body["artifacts"].append({**_entry(body, "ccf.half-life-table"), "key": BARE_HALF_LIFE_KEY})
    manifest = load_artifact(yaml.safe_dump(body, sort_keys=True), DEPLOYMENT_MANIFEST)
    assert isinstance(manifest, DeploymentManifest)

    with pytest.raises(ValueError) as raised:
        manifest_under_tenant(manifest, {}, None, tenant=TENANT)

    _assert_named(raised.value, authored=(HALF_LIFE_KEY, BARE_HALF_LIFE_KEY), placed=HALF_LIFE_KEY)


# ---------------------------------------------------------------------------
# The paved road: `open_product` boots each question through `load_config_and_boot`.
# ---------------------------------------------------------------------------


def test_the_paved_road_refuses_a_config_whose_sections_place_to_one_key(tmp_path: pathlib.Path) -> None:
    """``debt_profile:`` keyed onto the ``half_life:`` section's placed key: refused at the first question's boot.

    Before the guard the same question met the late ``TypeError`` instead (a
    ``DebtProfile`` registered under the half-life class), after the boot had
    registered the entries ahead of it. The paved road boots nothing at open, so
    the boot refusal arrives from ``answer``, as every boot refusal there does.
    """
    from tests.deployment.test_replay_binding import TENANT as PAVED_TENANT
    from tests.products import test_paved_road as paved

    placed = f"{PAVED_TENANT}/half_life"
    config = paved._config()
    config["debt_profile"] = {"key": placed, **config["debt_profile"]}
    root = paved._write_tree(tmp_path, config=config)

    with paved._open(root, tmp_path / "scratch") as opened:
        with pytest.raises((ValueError, TypeError)) as raised:
            opened.answer(paved._question(opened))

    _assert_named(raised.value, authored=("half_life", placed), placed=placed, tenant=PAVED_TENANT)
