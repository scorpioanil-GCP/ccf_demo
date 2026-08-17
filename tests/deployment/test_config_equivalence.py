"""`D-IMPL-136` §10's compatibility commitment, proved rather than argued —
half A: the whole boot path, both forms, over a synthetic fixture.

Whitepaper §7.8 (Control Plane artifacts, typed and versioned) and §7.10 (a
decision resolves the configuration in force when it was made); CLAUDE.md
§6.4 and §10 for the SDK-defined single-file loader `D-IMPL-134` and
`D-IMPL-136` commit to. Design spec
`docs/superpowers/specs/2026-08-14-ccf-config-consolidation-design.md` §3's
argument — merging artifacts into one file does not collapse their version
identities, because `ArtifactPin.version` **is** a content hash,
`canonical_bytes` addresses the parsed object, and
`~ccf.deployment.manifest.py` content-addresses the parsed contract rather
than the file bytes — was correct and verified by inspection before this plan
set was written. An argument is not a regression test. This module turns it
into one.

**What this module enforces, exactly.**

1. The same deployment, authored once as a manifest plus documents and once
   as a single `ccf_config.yaml`, boots to an **equal** `ResolvedPins` —
   compared as `model_dump_json()`, the same comparison
   `tests/deployment/test_manifest.py::test_two_loads_of_one_manifest_produce_an_identical_pin_set`
   uses, extended from two runs of one form to one run of each form.
2. `BootedFabric.artifacts` is equal key for key, by `canonical_bytes` of
   each parsed artifact, and the key **sets** are equal.
3. `tenant_id` and `survivor_cap` are equal.
4. Non-vacuous: the pin set is asserted non-empty and carries at least five
   entries.
5. A negative control: perturbing one value in the single-file form (a
   different `half_life_seconds`) makes exactly **one** pin version differ
   and leaves every other pin equal to the unperturbed boot.

**Scope.** The compared artifact set is restricted to what the config form
can express: no `ccf.signal-batch` entry appears on either side, because a
single-file `ccf_config.yaml` has no `signal_batch` section by design (see
`~ccf.deployment.config`'s own module docstring, *"What a `ccf_config.yaml`
cannot express, named rather than discovered"*). Named here rather than
silently omitted.

**What this module does not enforce.** It does not prove the two forms agree
on a *real, committed* deployment — that is half B,
`tests/examples/test_s1_00_config_equivalence.py`, which reads HW-1's
committed multi-file documents (read-only) against a hand-authored
single-file fixture and compares content addresses without booting. This
module's corpus is synthetic and lives entirely under `tmp_path`, built from
one set of Python literals shared by both authoring forms in this same
module — two serialisations of one source, so there is no duplicated corpus
to let drift.
"""

from __future__ import annotations

import pathlib
from typing import Any

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot, load_config_and_boot

from tests.deployment.conftest import manifest_document, write_artifact

#: Fixture vocabulary. Test-side names, never SDK values (CINV-01).
TENANT = "s1-00-equivalence-tenant"

#: --- the one Python literal both authoring forms serialise -------------------
#:
#: Six register-role artifacts: `product_class`, one `operators:` entry, and
#: four reserved sections. `request_contract` and `debt_profile` are omitted —
#: not load-bearing for this proof, and their absence keeps the fixture to
#: exactly the sections whose derived key order this module has to state
#: explicitly (below) for the two `ResolvedPins` to compare byte for byte.

_HALF_LIFE_ENTRY: dict[str, Any] = {
    "half_life_seconds": 3600,
    "decay_driver": "s1-00-equivalence-fixture",
    "supersession_event": "s1-00-equivalence-fixture-superseded",
}
_RESOLUTION_RULE: dict[str, Any] = {
    "match_key": "widget_ref",
    "entity_class": "widget",
    "identity_keys": ["widget_ref"],
    "attribute_keys": ["label"],
}
_PRODUCT_CLASS_BODY: dict[str, Any] = {
    "schema_name": "equivalence.fixture-product",
    "schema_version": "1.0.0",
    "ttl_anchor": "from_decision",
    "assembly_mode": "algorithmic",
    "max_ttl_key": "equivalence/fixture-product/max-ttl",
    "required_operator_keys": ["temporal.as-of-boundary"],
}
_TEMPORAL_PARAMS: dict[str, Any] = {"require_valid_at_boundary": True}
_PERSPECTIVE_BODY: dict[str, Any] = {
    "principal_id": "equivalence-principal",
    # `analyst` is `Perspective.role` — content, not the `ManifestEntry.role`
    # override — exercising the same collision resolution `16-29` shipped
    # (`test_default_perspectives_own_role_field_survives_as_content`).
    "role": "analyst",
}
_POLICY_DECLARATION: dict[str, Any] = {"regime": "equivalence-fixture-regime"}
_POLICY_CLASS_ID = "fixture.equivalence-policy-bundle"

#: The derived key order `~ccf.deployment.config.derive_deployment` produces
#: for this literal: `product_class` first, then `operators:` sorted (one
#: entry), then the reserved sections in the module's own fixed order
#: (`request_contract`, `resolution`, `half_life`, `debt_profile`, `policy`,
#: `default_perspective` — skipping the four this fixture omits). The
#: multi-file manifest below declares its `artifacts:` in this same order, so
#: the two `ResolvedPins.entries` tuples compare equal position for position,
#: not merely as sets.
_KEY_ORDER = (
    "product_class",
    "temporal.as-of-boundary",
    "resolution",
    "half_life",
    "policy",
    "default_perspective",
)


def _config_document(*, half_life_seconds: int = 3600) -> dict[str, Any]:
    """The single-file serialisation of the one source literal above."""
    half_life_entry = dict(_HALF_LIFE_ENTRY, half_life_seconds=half_life_seconds)
    return {
        "semver": "1.0.0",
        "tenant_id": TENANT,
        "backend": "sqlite",
        "product_class": dict(_PRODUCT_CLASS_BODY),
        "operators": {"temporal.as-of-boundary": dict(_TEMPORAL_PARAMS)},
        "resolution": {"entity_rules": [dict(_RESOLUTION_RULE)]},
        "half_life": {"widget": half_life_entry},
        "policy": {
            "class_id": _POLICY_CLASS_ID,
            "role": "register",
            "registration": "typed",
            **_POLICY_DECLARATION,
        },
        "default_perspective": dict(_PERSPECTIVE_BODY),
    }


def _multifile_deployment(
    root: pathlib.Path, *, half_life_seconds: int = 3600
) -> pathlib.Path:
    """The manifest-plus-documents serialisation of the same source literal.

    Built with the conftest's own `manifest_document` / `write_artifact`
    helpers — the artifact bodies are the same Python literals `_config_document`
    reads, wrapped exactly as each class's own contract requires (a property
    of the contract, not of either loader), never hand-copied a second time.
    """
    root.mkdir(parents=True, exist_ok=True)
    half_life_entry = dict(_HALF_LIFE_ENTRY, half_life_seconds=half_life_seconds)
    write_artifact(
        root,
        "product-class.yaml",
        {"semver": "1.0.0", **_PRODUCT_CLASS_BODY},
    )
    write_artifact(
        root,
        "temporal.yaml",
        {"semver": "1.0.0", **_TEMPORAL_PARAMS},
    )
    write_artifact(
        root,
        "resolution.yaml",
        {"semver": "1.0.0", "entity_rules": [_RESOLUTION_RULE]},
    )
    write_artifact(
        root,
        "half-life.yaml",
        {"semver": "1.0.0", "entries": {"widget": half_life_entry}},
    )
    write_artifact(
        root,
        "policy.yaml",
        {
            "semver": "1.0.0",
            "class_id": _POLICY_CLASS_ID,
            "declaration": _POLICY_DECLARATION,
        },
    )
    write_artifact(
        root,
        "perspective.yaml",
        {"semver": "1.0.0", **_PERSPECTIVE_BODY},
    )
    body = manifest_document(
        tenant_id=TENANT,
        resolution_spec_key="resolution",
        policy_bundle_key="policy",
        artifacts=[
            {
                "path": "product-class.yaml",
                "key": "product_class",
                "class_id": "ccf.product-class",
                "role": "register",
                "registration": "typed",
            },
            {
                "path": "temporal.yaml",
                "key": "temporal.as-of-boundary",
                "class_id": "ccf.operator-parameters.temporal",
                "role": "register",
                "registration": "typed",
            },
            {
                "path": "resolution.yaml",
                "key": "resolution",
                "class_id": "ccf.resolution-spec",
                "role": "register",
                "registration": "typed",
            },
            {
                "path": "half-life.yaml",
                "key": "half_life",
                "class_id": "ccf.half-life-table",
                "role": "register",
                "registration": "typed",
            },
            {
                "path": "policy.yaml",
                "key": "policy",
                "class_id": _POLICY_CLASS_ID,
                "role": "register",
                "registration": "typed",
            },
            {
                "path": "perspective.yaml",
                "key": "default_perspective",
                "class_id": "ccf.perspective",
                "role": "register",
                "registration": "typed",
            },
        ],
    )
    return write_artifact(root, "manifest.yaml", body)


def test_both_forms_boot_to_an_equal_resolved_pins_and_equal_artifacts(
    tmp_path: pathlib.Path,
) -> None:
    manifest_path = _multifile_deployment(tmp_path / "multifile")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = write_artifact(config_dir, "ccf_config.yaml", _config_document())

    multifile = load_and_boot(
        manifest_path,
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(tmp_path / "multifile.sqlite3")},
    )
    try:
        multifile_pins_json = multifile.pins.model_dump_json()
        multifile_artifacts = dict(multifile.artifacts)
        multifile_tenant = multifile.tenant_id
        multifile_survivor_cap = multifile.survivor_cap
    finally:
        multifile.handle.close()

    config = load_config_and_boot(
        config_path,
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(tmp_path / "config.sqlite3")},
    )
    try:
        config_pins_json = config.pins.model_dump_json()
        config_artifacts = dict(config.artifacts)
        config_tenant = config.tenant_id
        config_survivor_cap = config.survivor_cap
    finally:
        config.handle.close()

    # --- non-vacuity: a derivation that silently produced nothing cannot pass
    assert multifile.pins.entries
    assert len(multifile.pins.entries) >= 5
    assert config.pins.entries
    assert len(config.pins.entries) >= 5

    # --- the pin set: equal, entry for entry, in manifest order
    assert [pin.key for pin in multifile.pins.entries] == list(_KEY_ORDER)
    assert [pin.key for pin in config.pins.entries] == list(_KEY_ORDER)
    assert multifile_pins_json == config_pins_json
    for pin in multifile.pins.entries:
        assert pin.version == config.pins.version_for(pin.key), (
            f"content address diverges at key {pin.key!r}:"
            f" multifile={pin.version} config={config.pins.version_for(pin.key)}"
        )

    # --- BootedFabric.artifacts: equal key for key, by canonical_bytes
    assert set(multifile_artifacts) == set(config_artifacts) == set(_KEY_ORDER)
    for key in _KEY_ORDER:
        assert canonical_bytes(multifile_artifacts[key]) == canonical_bytes(
            config_artifacts[key]
        ), f"parsed artifact diverges at key {key!r}"

    # --- tenant_id and survivor_cap
    assert multifile_tenant == config_tenant == TENANT
    assert multifile_survivor_cap == config_survivor_cap is None


def test_perturbing_the_single_file_form_moves_exactly_one_pin(
    tmp_path: pathlib.Path,
) -> None:
    """The negative control. Without it, the equality assertions above would
    pass against an implementation that compared two copies of the same
    thing rather than two independently-derived registrations."""
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    baseline_path = write_artifact(baseline_dir, "ccf_config.yaml", _config_document())
    baseline = load_config_and_boot(
        baseline_path,
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(tmp_path / "baseline.sqlite3")},
    )
    try:
        baseline_pins = {pin.key: pin.version for pin in baseline.pins.entries}
    finally:
        baseline.handle.close()

    perturbed_dir = tmp_path / "perturbed"
    perturbed_dir.mkdir()
    perturbed_path = write_artifact(
        perturbed_dir,
        "ccf_config.yaml",
        _config_document(half_life_seconds=7200),
    )
    perturbed = load_config_and_boot(
        perturbed_path,
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(tmp_path / "perturbed.sqlite3")},
    )
    try:
        perturbed_pins = {pin.key: pin.version for pin in perturbed.pins.entries}
    finally:
        perturbed.handle.close()

    assert set(baseline_pins) == set(perturbed_pins) == set(_KEY_ORDER)
    differing = {
        key for key in _KEY_ORDER if baseline_pins[key] != perturbed_pins[key]
    }
    assert differing == {"half_life"}, (
        f"expected exactly {{'half_life'}} to differ; got {sorted(differing)}"
    )
