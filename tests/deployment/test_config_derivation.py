"""`derive_deployment` — the derivation table proved section by section.

Whitepaper §7.8 (Control Plane artifacts, typed and versioned); CLAUDE.md
§6.4 and §10 for the SDK-defined single-file loader `D-IMPL-134` and
`D-IMPL-136` commit to. Design spec
`docs/superpowers/specs/2026-08-14-ccf-config-consolidation-design.md` §6,
§6.1, §6.2, §6.3, §11.1, §11.2 and §12 is the mechanism these tests hold the
implementation to.

**What these tests enforce, exactly.**

1. The reserved-section table is cross-checked against
   `~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` rather than eyeballed.
2. Each of the five SDK-owned sections derives its `ccf.*` class id,
   `role: register`, `registration: typed`, silently — no field stated.
3. `half_life` materialises wrapped under `entries`; the other four SDK-owned
   sections materialise at the document's top level.
4. An `operators:` entry derives its class id from the segment before the
   first `.`, built from a single prefix constant rather than enumerated.
5. Every derived `path` is the literal authoring filename — a one-element
   set over the whole entry tuple.
6. Every materialised document carries the config's own top-level `semver`.
7. `key`, `class_id`, `role` and `registration` overrides win over the
   derived value; `path` does not accept one (covered in
   `test_config_refusals.py`, R3).
8. The one collision the shipped SDK classes hit —
   `~ccf.projection.plan.Perspective`'s own `role` field colliding with
   `ManifestEntry.role` — resolves in favour of content, and design spec
   §8.1's own worked `default_perspective` example derives correctly.
9. The HW-1 transcription (`tests/deployment/test_config_document.py
   ::HW1_SINGLE_FILE_DOCUMENT`) derives the same eight
   `(class_id, role, registration)` triples as
   `examples/s1-00-companies-over-revenue/artifacts/config/manifest.yaml`,
   with exactly one `role: load`, and every materialised document validates
   through `parse_artifact` against the class its own entry names.
10. `derive_deployment` is pure: no file read, no environment read, and
    calling it twice on an equal config produces equal results.

**What these tests do not enforce.** Nothing here registers an artifact,
boots a fabric, or asserts the derived manifest matches the *multi-file*
`ccf.deployment-manifest` document byte-for-byte — that is `16-30`'s
equivalence proof. The five refusals live in `test_config_refusals.py`.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    POLICY_CONSTRAINT,
    DeploymentConfig,
    ManifestEntry,
    PolicyConstraint,
    parse_artifact,
)
from ccf.deployment import config as config_module
from ccf.deployment.classes import (
    SDK_ARTIFACT_CLASSES,
    resolve_artifact_class,
)
from ccf.deployment.config import DerivedDeployment, derive_deployment

from tests.deployment.test_config_document import HW1_SINGLE_FILE_DOCUMENT

#: `examples/s1-00-companies-over-revenue/artifacts/config/manifest.yaml`'s
#: own eight entries, as `(class_id, role, registration)` triples keyed by
#: the multi-file manifest's own key — read-only reference material, quoted
#: here rather than loaded from the example (Dave's dual-model ruling,
#: 2026-08-14 — HW-1 stays multi-file and is not read by this loader).
_HW1_MANIFEST_TRIPLES: dict[str, tuple[str, str, str]] = {
    "resolution-spec": ("ccf.resolution-spec", "register", "typed"),
    "policy-bundle": ("hw1.policy-bundle", "register", "typed"),
    "perspective": ("ccf.perspective", "register", "typed"),
    "product-class": ("ccf.product-class", "register", "typed"),
    "half-life-table": ("ccf.half-life-table", "register", "typed"),
    "temporal": ("ccf.operator-parameters.temporal", "register", "typed"),
    "debt-profile": ("ccf.debt-profile", "register", "typed"),
    "request-contract": ("hw1.request-contract", "load", "typed"),
}


def _minimal(**overrides: Any) -> DeploymentConfig:
    """The smallest `DeploymentConfig` `derive_deployment` accepts, plus a
    `resolution:` and `policy:` section so the two boot pointers always
    resolve — most derivation tests are not about R5, and building it fresh
    per call means a mutated section in one test cannot leak into another.
    """
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "product_class": {
            "schema_name": "fixture.product",
            "required_operator_keys": [],
        },
        "resolution": {"entity_rules": []},
        "policy": {
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
            "regime": "fixture-regime",
        },
    }
    document.update(overrides)
    parsed = parse_artifact(document, DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    return parsed


def _entry_by_key(derived: DerivedDeployment, key: str) -> ManifestEntry:
    matches = [entry for entry in derived.manifest.artifacts if entry.key == key]
    assert len(matches) == 1, f"expected exactly one entry keyed {key!r}"
    return matches[0]


# --- 1. the reserved-section table, cross-checked rather than eyeballed -------


def test_reserved_section_table_ccf_ids_are_all_sdk_artifact_classes() -> None:
    for section_name, (default_class_id, _wrapper) in (
        config_module._RESERVED_SECTIONS.items()
    ):
        if default_class_id is None:
            continue
        assert default_class_id in SDK_ARTIFACT_CLASSES, (
            f"{section_name!r} names {default_class_id!r}, which is not in"
            " SDK_ARTIFACT_CLASSES — the reserved-section table has drifted"
            " from ccf/deployment/classes.py"
        )


def test_exactly_two_reserved_sections_are_adopter_owned() -> None:
    """`D-IMPL-138`(a): `policy` and `request_contract`, and no others."""
    adopter_owned = {
        name
        for name, (default_class_id, _wrapper) in config_module._RESERVED_SECTIONS.items()
        if default_class_id is None
    }
    assert adopter_owned == {"policy", "request_contract"}


# --- 2 & 3. the five SDK-owned sections: silent derivation, materialisation ---


@pytest.mark.parametrize(
    ("section", "class_id", "wrapped_under"),
    [
        ("product_class", "ccf.product-class", None),
        ("resolution", "ccf.resolution-spec", None),
        ("half_life", "ccf.half-life-table", "entries"),
        ("debt_profile", "ccf.debt-profile", None),
        ("default_perspective", "ccf.perspective", None),
    ],
)
def test_sdk_owned_section_derives_silently(
    section: str, class_id: str, wrapped_under: str | None
) -> None:
    body: dict[str, Any] = {"x": "y"} if section != "half_life" else {
        "company": {
            "half_life_seconds": 1,
            "decay_driver": "d",
            "supersession_event": "s",
        }
    }
    if section == "default_perspective":
        body = {"principal_id": "p", "role": "analyst"}
    elif section == "debt_profile":
        body = {
            "risk_sensitivity": "1.0",
            "forced_llm_threshold": "0.2",
            "fail_closed_threshold": "0.6",
        }
    elif section == "resolution":
        body = {"entity_rules": []}
    elif section == "product_class":
        body = {"schema_name": "x", "required_operator_keys": []}

    config = _minimal(**{section: body})
    derived = derive_deployment(config)
    entry = _entry_by_key(derived, section)
    assert entry.class_id == class_id
    assert entry.role == "register"
    assert entry.registration == "typed"

    document = derived.documents[section]
    assert document["semver"] == config.semver
    if wrapped_under is None:
        for field, value in body.items():
            assert document[field] == value
        assert "entries" not in document or section == "half_life"
    else:
        assert document[wrapped_under] == body


def test_default_perspectives_own_role_field_survives_as_content() -> None:
    """Design spec §8.1's own worked example: `role: analyst` is
    `Perspective.role`, not a `ManifestEntry.role` override — the one
    collision the shipped SDK classes hit, resolved in favour of content.
    """
    config = _minimal(
        default_perspective={"principal_id": "revenue-screening-desk-1", "role": "analyst"}
    )
    derived = derive_deployment(config)
    entry = _entry_by_key(derived, "default_perspective")
    assert entry.role == "register"  # silently derived, not read from body
    document = derived.documents["default_perspective"]
    assert document["role"] == "analyst"  # the section's own content, intact


# --- 4. operator entries: category-built class id -----------------------------


def test_operator_entry_derives_category_prefixed_class_id() -> None:
    config = _minimal(
        product_class={
            "schema_name": "x",
            "required_operator_keys": ["temporal.as-of-boundary"],
        },
        operators={"temporal.as-of-boundary": {"require_valid_at_boundary": True}},
    )
    derived = derive_deployment(config)
    entry = _entry_by_key(derived, "temporal.as-of-boundary")
    assert entry.class_id == "ccf.operator-parameters.temporal"
    assert entry.role == "register"
    assert entry.registration == "typed"
    document = derived.documents["temporal.as-of-boundary"]
    assert document == {"semver": "1.0.0", "require_valid_at_boundary": True}


def test_operator_class_ids_are_built_not_enumerated() -> None:
    """`command grep -c "ccf.operator-parameters" src/ccf/deployment/config.py`
    must find exactly the one prefix constant — asserted here so a
    regression is caught by the suite, not only by the acceptance grep.
    """
    source = inspect.getsource(config_module)
    assert source.count("ccf.operator-parameters") == 1


# --- 4b. policy_constraints: one entry per label ------------------------------


def test_policy_constraints_section_derives_one_entry_per_label() -> None:
    """`24.6-L-07`, `D-IMPL-253` Q3: *"A policy constraint has independent
    identity, version, effectivity and authority and should not disappear
    inside another bundle."* One manifest entry per label is what that means
    mechanically — the `operators` precedent, applied to a second dynamically
    keyed section. Each derived document validates as a `PolicyConstraint`.
    """
    config = _minimal(
        policy_constraints={
            "tolerance-ceiling": {
                "policy_id": "fixture-regime",
                "applies_to": {"product_class": "fixture.product"},
                "parameter": "fixture_parameter",
                "operator": "maximum",
                "value": "0.2",
                "source_authority": "fixture-authority",
                "effective_from": "2026-01-01T00:00:00Z",
                "reason": "fixture reason",
            },
            "depth-floor": {
                "policy_id": "fixture-regime",
                "applies_to": {},
                "parameter": "fixture_depth",
                "operator": "minimum",
                "value": "1",
                "source_authority": "fixture-authority",
                "effective_from": "2026-01-01T00:00:00Z",
                "reason": "fixture reason",
            },
        }
    )
    derived = derive_deployment(config)

    keys = [
        entry.key
        for entry in derived.manifest.artifacts
        if entry.class_id == "ccf.policy-constraint"
    ]
    assert sorted(keys) == [
        "policy_constraints.depth-floor",
        "policy_constraints.tolerance-ceiling",
    ]

    for key in keys:
        entry = _entry_by_key(derived, key)
        assert entry.class_id == "ccf.policy-constraint"
        assert entry.role == "register"
        assert entry.registration == "typed"
        document = derived.documents[key]
        assert document["semver"] == config.semver
        parsed = parse_artifact(document, POLICY_CONSTRAINT)
        assert isinstance(parsed, PolicyConstraint)
        assert parsed.policy_id == "fixture-regime"


def test_a_config_naming_no_policy_constraints_derives_none() -> None:
    """The positive control for the section above, and the compatibility
    claim: a config written before this section existed derives exactly the
    entries it always did."""
    derived = derive_deployment(_minimal())
    assert not [
        entry
        for entry in derived.manifest.artifacts
        if entry.class_id == "ccf.policy-constraint"
    ]


# --- 5, 6. path and semver -----------------------------------------------------


def test_every_derived_path_is_the_literal_config_filename() -> None:
    derived = derive_deployment(_minimal(), config_filename="ccf_config.yaml")
    paths = {entry.path for entry in derived.manifest.artifacts}
    assert paths == {"ccf_config.yaml"}


def test_config_filename_argument_is_honoured() -> None:
    derived = derive_deployment(_minimal(), config_filename="deployment.yaml")
    paths = {entry.path for entry in derived.manifest.artifacts}
    assert paths == {"deployment.yaml"}


# --- 7. overrides win ----------------------------------------------------------


def test_explicit_key_override_changes_the_entry_key_and_the_boot_pointer() -> None:
    config = _minimal(
        resolution={"entity_rules": [], "key": "custom-resolution-key"}
    )
    derived = derive_deployment(config)
    keys = {entry.key for entry in derived.manifest.artifacts}
    assert "custom-resolution-key" in keys
    assert "resolution" not in keys
    assert derived.manifest.resolution_spec_key == "custom-resolution-key"


def test_explicit_class_id_override_wins_and_is_still_checked() -> None:
    config = _minimal(
        debt_profile={
            "risk_sensitivity": "1.0",
            "forced_llm_threshold": "0.2",
            "fail_closed_threshold": "0.6",
            "class_id": "ccf.debt-profile",  # redundant, but explicit
        }
    )
    derived = derive_deployment(config)
    entry = _entry_by_key(derived, "debt_profile")
    assert entry.class_id == "ccf.debt-profile"


def test_role_override_contradicting_the_sdk_fixed_role_is_refused() -> None:
    """`ccf.signal-batch` is the one class `SDK_ARTIFACT_ROLES` fixes
    (D-IMPL-80). Reached here through an adopter-owned section's `class_id`
    override, so the same check an authored manifest holds every entry to
    also holds a derived one, override and all."""
    config = _minimal(
        policy={
            "class_id": "ccf.signal-batch",
            "role": "register",
            "registration": "typed",
        }
    )
    with pytest.raises(ValueError, match="D-IMPL-80"):
        derive_deployment(config)


def test_registration_override_contradicting_the_sdk_fixed_path_is_refused() -> None:
    """`ccf.workflow-definition` is author-versioned
    (`SDK_VERSIONED_ARTIFACT_CLASSES`); declaring `registration: typed`
    against it is refused by `refuse_registration_the_sdk_fixes`
    (D-IMPL-85), reached here through the same override path."""
    config = _minimal(
        request_contract={
            "class_id": "ccf.workflow-definition",
            "role": "load",
            "registration": "typed",
        }
    )
    with pytest.raises(ValueError, match="D-IMPL-85"):
        derive_deployment(config)


# --- 9. the HW-1 transcription --------------------------------------------------


def _hw1_derived() -> DerivedDeployment:
    config = parse_artifact(HW1_SINGLE_FILE_DOCUMENT, DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig)
    return derive_deployment(config)


def test_hw1_transcription_derives_eight_entries_matching_hw1s_manifest() -> None:
    derived = _hw1_derived()
    assert len(derived.manifest.artifacts) == 8

    derived_triples = {
        (entry.class_id, entry.role, entry.registration)
        for entry in derived.manifest.artifacts
    }
    expected_triples = set(_HW1_MANIFEST_TRIPLES.values())
    assert derived_triples == expected_triples, (
        "derived (class_id, role, registration) triples do not match HW-1's"
        f" manifest.yaml: derived={sorted(derived_triples)}"
        f" expected={sorted(expected_triples)}"
    )

    load_role_count = sum(
        1 for entry in derived.manifest.artifacts if entry.role == "load"
    )
    assert load_role_count == 1


def test_hw1_transcription_documents_all_validate() -> None:
    derived = _hw1_derived()
    validated = 0
    for entry in derived.manifest.artifacts:
        document = derived.documents[entry.key]
        artifact_class = resolve_artifact_class(entry.class_id)
        parsed = parse_artifact(document, artifact_class)
        assert parsed is not None
        validated += 1
    assert validated == 8


def test_hw1_transcription_boot_pointers_derive_from_section_names() -> None:
    derived = _hw1_derived()
    assert derived.manifest.resolution_spec_key == "resolution"
    assert derived.manifest.policy_bundle_key == "policy"


# --- 10. purity ------------------------------------------------------------------


def test_deriving_twice_from_one_config_produces_equal_results() -> None:
    config = _minimal(
        half_life={
            "company": {
                "half_life_seconds": 1,
                "decay_driver": "d",
                "supersession_event": "s",
            }
        }
    )
    first = derive_deployment(config)
    second = derive_deployment(config)
    assert first.manifest == second.manifest
    assert first.documents == second.documents


def test_derive_deployment_reads_no_file_and_no_environment() -> None:
    """A source scan, not an integration test: `derive_deployment` and its
    private helpers must not call `open`, touch `os.environ`, or construct
    a `pathlib.Path` — any of those would make this module's `derives, does
    not read` boundary a docstring claim rather than a fact.

    Scoped to `derive_deployment` itself plus every private (``_``-prefixed)
    function the module declares — read dynamically off the module rather
    than hand-listed, so a new private helper is covered automatically and
    the scope cannot silently narrow. **Not** a whole-module scan as of
    `16-30`: `ccf.deployment.config` also carries `load_config_and_boot`,
    the front door that reads a real `ccf_config.yaml` off disk and is
    documented as doing exactly that (`D-IMPL-136`) — the same relationship
    `~ccf.deployment.manifest.load_and_boot` (I/O) has to
    `~ccf.deployment.config.derive_deployment` (pure), one module over. A
    whole-module scan would refuse the loader this plan exists to add;
    this scan still refuses the derivation reading a file or an environment
    variable, which is the property the docstring actually claims.
    """
    sources = [inspect.getsource(config_module.derive_deployment)]
    for name, obj in vars(config_module).items():
        if (
            name.startswith("_")
            and inspect.isfunction(obj)
            # Excludes `_preflight_entries` / `_preflight_adapter` /
            # `_register_and_boot` / `_resolve_secret_references` /
            # `_resolve_tenant` — imported from `~ccf.deployment.manifest`
            # for `load_config_and_boot` (`16-30`) to call, not defined here.
            # `derive_deployment`'s purity claim is about this module's own
            # derivation code; the manifest module's own I/O is covered by
            # `~ccf.deployment.manifest`'s own tests, not this one.
            and obj.__module__ == config_module.__name__
        ):
            sources.append(inspect.getsource(obj))
    source = "\n".join(sources)
    for forbidden in ("open(", "os.environ", "pathlib.Path(", "Path("):
        assert forbidden not in source, (
            f"{forbidden!r} appears in derive_deployment or one of its private"
            " helpers — derive_deployment must be pure over its argument"
        )
