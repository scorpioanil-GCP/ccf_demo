"""The five refusals `derive_deployment` must not soften.

Whitepaper §7.8; CLAUDE.md §6.4 and §10; design spec
`docs/superpowers/specs/2026-08-14-ccf-config-consolidation-design.md` §6.1
(`D-IMPL-134`'s narrowing), §11.1 (`path` and key uniqueness) and §11.2 (the
operator-set divergence). `D-IMPL-80` and `D-IMPL-85` are the rulings R1
defends; `D-IMPL-138`(a) is the three-line correction that makes an
adopter-owned section's `class_id` a fourth thing R1 must also refuse when
absent.

**What these tests enforce, exactly.**

- **R1** — an adopter-owned section (`policy`, `request_contract`) missing
  `class_id`, `role` or `registration` is refused, naming the section, every
  missing field together, and both `D-IMPL-80` and `D-IMPL-85`. A negative
  control proves the refusal is not blanket — the section that states all
  three parses and derives. A second positive control proves the narrowing
  is not over-applied: the five SDK-owned sections omitting `role` and
  `registration` derive silently.
- **R2** — the declared (`product_class.required_operator_keys`) and
  configured (`operators:`) operator sets diverging, in **both**
  directions, is refused naming both sites. Agreeing sets are the ordinary
  case and derive with no refusal.
- **R3** — a section naming `path:` is refused; `path` is the one field
  with no override syntax at all.
- **R4** — a key collision after `key:` overrides is refused, delegated to
  `DeploymentManifest`'s own `_keys_are_unique`. Duplicate *paths* are not a
  collision — every derived entry shares one path by construction, and a
  derivation of eight same-path entries succeeds.
- **R5** — a config naming neither a `resolution:`/`policy:` section nor an
  explicit `resolution_spec_key`/`policy_bundle_key` is refused with a
  message about what `boot()` needs, not a `DeploymentManifest` field-path
  error three layers down.
- An **empty** section (heading present, body absent) is refused
  distinguishably from an **absent** one, which derives nothing and raises
  nothing.

**What these tests do not enforce.** The derivation table itself (which
class id, which materialisation shape) — that is `test_config_derivation.py`.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.controlplane.artifacts import DEPLOYMENT_CONFIG, DeploymentConfig, parse_artifact
from ccf.deployment.config import derive_deployment


def _minimal(**overrides: Any) -> DeploymentConfig:
    """The smallest config that derives cleanly, ``overrides`` applied at the
    top level. A test that wants to break one thing overrides exactly that
    section; everything else stays valid so the refusal under test is the
    only one that can fire.
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


# --- R1 — adopter-owned requiredness -------------------------------------------


@pytest.mark.parametrize("section", ["policy", "request_contract"])
def test_r1_adopter_owned_section_missing_all_three_is_refused(section: str) -> None:
    config = _minimal(**{section: {"anything": "adopter content, no bookkeeping"}})
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    message = str(raised.value)
    assert repr(section) in message
    assert "'class_id'" in message
    assert "'role'" in message
    assert "'registration'" in message
    assert "D-IMPL-80" in message
    assert "D-IMPL-85" in message


def test_r1_partial_omission_names_only_the_missing_fields() -> None:
    config = _minimal(
        policy={
            "regime": "fixture-regime",
            "class_id": "acme.policy-bundle",
            "role": "register",
            # registration omitted
        }
    )
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    message = str(raised.value)
    assert "'registration'" in message
    assert "'class_id'" not in message
    assert "'role'" not in message


def test_r1_negative_control_all_three_stated_derives() -> None:
    """Without this, R1's positive test would pass against an implementation
    that refuses *every* adopter section — which would break HW-1's shape
    entirely."""
    config = _minimal(
        policy={
            "regime": "fixture-regime",
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
        }
    )
    derived = derive_deployment(config)
    keys = {entry.key for entry in derived.manifest.artifacts}
    assert "policy" in keys


@pytest.mark.parametrize(
    "section",
    ["product_class", "resolution", "half_life", "debt_profile", "default_perspective"],
)
def test_r1_does_not_over_reach_sdk_owned_sections_derive_silently(
    section: str,
) -> None:
    """`D-IMPL-134`'s narrowing demonstrated in the direction R1 must not
    swallow: an SDK-owned section stating no `role` and no `registration`
    still derives — a later "tightening" that made them required everywhere
    would fail this test.
    """
    bodies: dict[str, dict[str, Any]] = {
        "product_class": {"schema_name": "x", "required_operator_keys": []},
        "resolution": {"entity_rules": []},
        "half_life": {
            "company": {
                "half_life_seconds": 1,
                "decay_driver": "d",
                "supersession_event": "s",
            }
        },
        "debt_profile": {
            "risk_sensitivity": "1.0",
            "forced_llm_threshold": "0.2",
            "fail_closed_threshold": "0.6",
        },
        "default_perspective": {"principal_id": "p", "role": "analyst"},
    }
    config = _minimal(**{section: bodies[section]})
    derived = derive_deployment(config)
    entry = next(e for e in derived.manifest.artifacts if e.key == section)
    assert entry.role == "register"
    assert entry.registration == "typed"


def test_r1_positive_and_negative_in_one_config() -> None:
    """The narrowing demonstrated in both directions in one derivation: the
    five SDK-owned sections stay silent while the two adopter-owned ones
    would be refused if incomplete — verified here by supplying all three
    explicitly and checking every entry still derives.
    """
    config = _minimal(
        product_class={"schema_name": "x", "required_operator_keys": []},
        resolution={"entity_rules": []},
        half_life={
            "company": {
                "half_life_seconds": 1,
                "decay_driver": "d",
                "supersession_event": "s",
            }
        },
        debt_profile={
            "risk_sensitivity": "1.0",
            "forced_llm_threshold": "0.2",
            "fail_closed_threshold": "0.6",
        },
        default_perspective={"principal_id": "p", "role": "analyst"},
        policy={
            "regime": "fixture-regime",
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
        },
    )
    derived = derive_deployment(config)
    assert len(derived.manifest.artifacts) == 6


# --- R2 — operator-set divergence -----------------------------------------------


def test_r2_declared_and_unconfigured_is_refused() -> None:
    config = _minimal(
        product_class={
            "schema_name": "x",
            "required_operator_keys": ["temporal.as-of-boundary"],
        },
    )
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    message = str(raised.value)
    assert "required_operator_keys" in message
    assert "operators:" in message
    assert "temporal.as-of-boundary" in message


def test_r2_configured_and_undeclared_is_refused() -> None:
    config = _minimal(
        product_class={"schema_name": "x", "required_operator_keys": []},
        operators={"temporal.as-of-boundary": {"require_valid_at_boundary": True}},
    )
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    message = str(raised.value)
    assert "required_operator_keys" in message
    assert "operators:" in message


def test_r2_message_names_both_sites_verbatim() -> None:
    config = _minimal(
        product_class={
            "schema_name": "x",
            "required_operator_keys": ["temporal.as-of-boundary"],
        },
    )
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    assert str(raised.value) == (
        "operator set divergence: product_class.required_operator_keys"
        " names ['temporal.as-of-boundary'] and the operators: section"
        " configures [], differing on ['temporal.as-of-boundary']; neither"
        " site is authoritative and only this deployment's author knows"
        " which is wrong (design spec §11.2) — refusing beats picking"
    )


def test_r2_negative_control_agreeing_sets_derive() -> None:
    config = _minimal(
        product_class={
            "schema_name": "x",
            "required_operator_keys": ["temporal.as-of-boundary"],
        },
        operators={"temporal.as-of-boundary": {"require_valid_at_boundary": True}},
    )
    derived = derive_deployment(config)
    keys = {entry.key for entry in derived.manifest.artifacts}
    assert "temporal.as-of-boundary" in keys


def test_r2_negative_control_zero_declared_zero_configured_derives() -> None:
    config = _minimal(
        product_class={"schema_name": "x", "required_operator_keys": []},
    )
    derived = derive_deployment(config)
    assert derived is not None


# --- R3 — path is not overridable -----------------------------------------------


def test_r3_a_section_naming_path_is_refused() -> None:
    config = _minimal(
        debt_profile={
            "risk_sensitivity": "1.0",
            "forced_llm_threshold": "0.2",
            "fail_closed_threshold": "0.6",
            "path": "somewhere-else.yaml",
        }
    )
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    message = str(raised.value)
    assert "'debt_profile'" in message
    assert "path" in message
    assert "not overridable" in message


def test_r3_adopter_owned_section_naming_path_is_also_refused() -> None:
    config = _minimal(
        policy={
            "regime": "fixture-regime",
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
            "path": "elsewhere.yaml",
        }
    )
    with pytest.raises(ValueError, match="not overridable"):
        derive_deployment(config)


# --- R4 — key collision, and the deliberate path-sharing asymmetry ------------


def test_r4_a_key_collision_after_overrides_is_refused() -> None:
    config = _minimal(
        resolution={"entity_rules": [], "key": "same-key"},
        debt_profile={
            "risk_sensitivity": "1.0",
            "forced_llm_threshold": "0.2",
            "fail_closed_threshold": "0.6",
            "key": "same-key",
        },
    )
    with pytest.raises(ValueError, match="declared twice"):
        derive_deployment(config)


def test_r4_eight_entries_sharing_one_path_succeeds() -> None:
    """The deliberate asymmetry `DeploymentManifest._keys_are_unique`'s own
    docstring records: paths may repeat, only keys may not. Asserted here so
    a later implementer cannot "fix" a non-problem by making paths vary."""
    config = _minimal(
        product_class={
            "schema_name": "x",
            "required_operator_keys": ["temporal.as-of-boundary"],
        },
        operators={"temporal.as-of-boundary": {"require_valid_at_boundary": True}},
        half_life={
            "company": {
                "half_life_seconds": 1,
                "decay_driver": "d",
                "supersession_event": "s",
            }
        },
        debt_profile={
            "risk_sensitivity": "1.0",
            "forced_llm_threshold": "0.2",
            "fail_closed_threshold": "0.6",
        },
        default_perspective={"principal_id": "p", "role": "analyst"},
        request_contract={
            "class_id": "acme.request-contract",
            "role": "load",
            "registration": "typed",
            "schema_name": "x",
        },
    )
    derived = derive_deployment(config)
    assert len(derived.manifest.artifacts) == 8
    assert {entry.path for entry in derived.manifest.artifacts} == {"ccf_config.yaml"}


# --- R5 — an unbootable manifest --------------------------------------------------


def test_r5_no_resolution_section_and_no_explicit_key_is_refused() -> None:
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "product_class": {"schema_name": "x", "required_operator_keys": []},
        "policy": {
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
            "regime": "r",
        },
    }
    config = parse_artifact(document, DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig)
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    message = str(raised.value)
    assert "resolution_spec_key" in message
    assert "boot()" in message
    assert "'resolution:'" in message


def test_r5_no_policy_section_and_no_explicit_key_is_refused() -> None:
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "product_class": {"schema_name": "x", "required_operator_keys": []},
        "resolution": {"entity_rules": []},
    }
    config = parse_artifact(document, DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig)
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    message = str(raised.value)
    assert "policy_bundle_key" in message
    assert "boot()" in message
    assert "'policy:'" in message


def test_r5_explicit_resolution_spec_key_substitutes_for_the_section() -> None:
    """Design spec §6.3: an explicit top-level value wins over the derived
    boot pointer, and the config need not carry the `resolution:` section at
    all as long as the named key resolves to a `role: register` entry —
    here, the entry the `resolution:` section under a `key:` override
    produces."""
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "product_class": {"schema_name": "x", "required_operator_keys": []},
        "resolution": {"entity_rules": [], "key": "elsewhere"},
        "resolution_spec_key": "elsewhere",
        "policy": {
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
            "regime": "r",
        },
    }
    config = parse_artifact(document, DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig)
    derived = derive_deployment(config)
    assert derived.manifest.resolution_spec_key == "elsewhere"


# --- the empty-vs-absent section distinction ------------------------------------


@pytest.mark.parametrize(
    "section",
    ["operators", "request_contract", "resolution", "half_life", "debt_profile", "policy", "default_perspective"],
)
def test_an_empty_section_is_refused_distinguishably_from_an_absent_one(
    section: str,
) -> None:
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "product_class": {"schema_name": "x", "required_operator_keys": []},
        "resolution": {"entity_rules": []},
        "policy": {
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
            "regime": "r",
        },
        section: None,  # heading present, body absent
    }
    config = parse_artifact(document, DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig)
    with pytest.raises(ValueError) as raised:
        derive_deployment(config)
    message = str(raised.value)
    assert repr(section) in message
    assert "present but empty" in message


def test_an_absent_section_raises_nothing_and_derives_nothing_for_it() -> None:
    config = _minimal()  # no 'half_life', no 'default_perspective', ...
    derived = derive_deployment(config)
    keys = {entry.key for entry in derived.manifest.artifacts}
    assert "half_life" not in keys
    assert "default_perspective" not in keys
    assert "half_life" not in derived.documents
