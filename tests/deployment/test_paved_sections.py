"""The three paved-road sections, the derived keys and the environment document (`D-IMPL-343`).

CLAUDE.md §6.4 and §10; the ruling of record is `D-IMPL-343` and its design
(``docs/D-IMPL-343-DESIGN.md`` §5.1–§5.3, §14 R-2/R-3/R-6/R-10). What these
tests hold the derivation to, exactly:

1. `ttl:` and `door:` derive on the TYPED path like `replay:` — one top-level
   entry each, `register`/`typed`, the config's own `semver` — and a config
   declaring neither derives byte-for-byte what it derived before.
2. A principal, a role, a URL or a credential written under `door:` is
   refused at derivation by name; a `door:` asserting another tenant is
   refused at derivation (R-6).
3. `agent:` derives on the VERSIONED path: no `semver` injected, the class
   fixed, `registration: versioned` fixed, the deployment's tenant filled or
   held equal, and the guard tables untouched — `ccf.agent-definition` stays
   out of the typed table (R-2).
4. `DerivedDeployment.keys` names every section's key and reaches the booted
   fabric.
5. The environment document holds names and refuses values, and resolves
   every declared variable at once with the document's own remedy.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    EGRESS_DOOR,
    TTL_BINDING,
    DeploymentConfig,
    EgressDoorBinding,
    TtlBinding,
    parse_artifact,
)
from ccf.deployment import config as config_module
from ccf.deployment.classes import SDK_ARTIFACT_CLASSES, SDK_VERSIONED_ARTIFACT_CLASSES
from ccf.deployment.config import derive_deployment
from ccf.deployment.environment import (
    ENVIRONMENT_DOCUMENT_NAME,
    EnvironmentDocument,
    EnvironmentMissing,
    load_environment_document,
    resolve_values,
)

TENANT = "paved-fixture"


def _minimal(**overrides: Any) -> DeploymentConfig:
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "tenant_id": TENANT,
        "backend": "sqlite",
        "product_class": {
            "schema_name": "fixture.product",
            "schema_version": "1.0.0",
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": "fixture/max-ttl",
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


def _door(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "producer_id": "fixture-egress",
        "producer_tenant": TENANT,
        "tool_description": "asks the fixture product a question",
        "required_scope": "ccf:egress",
    }
    body.update(overrides)
    return body


def _agent(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "artifact_version": "1.0.0",
        "name": "fixture-composer",
        "archetypes": ["context_assembly"],
        "context_contract": {"consumes": [{"product_class": "fixture.child", "schema_version": "1.0.0"}]},
        "perspective": {"role": "analyst", "selection_params": {}},
        "policy_regime": {"ref": f"ccf-artifact://{TENANT}/policy-bundle/x@1.0.0"},
        "halflife_debt_profile": {"ref": f"ccf-artifact://{TENANT}/debt-profile/x@1.0.0"},
        "instruction_bindings": [],
    }
    body.update(overrides)
    return body


# --- 1. the two typed sections ------------------------------------------------


def test_the_two_typed_sections_are_in_the_typed_table_and_the_agent_is_not() -> None:
    assert config_module._RESERVED_SECTIONS["ttl"] == (TTL_BINDING.class_id, None)
    assert config_module._RESERVED_SECTIONS["door"] == (EGRESS_DOOR.class_id, None)
    assert TTL_BINDING.class_id in SDK_ARTIFACT_CLASSES
    assert EGRESS_DOOR.class_id in SDK_ARTIFACT_CLASSES
    # R-2: the composing agent's class stays where D-IMPL-85 put it.
    for class_id in config_module._RESERVED_VERSIONED_SECTIONS.values():
        assert class_id in SDK_VERSIONED_ARTIFACT_CLASSES
        assert class_id not in SDK_ARTIFACT_CLASSES
    assert "agent" not in config_module._RESERVED_SECTIONS


def test_ttl_and_door_derive_one_typed_entry_each_carrying_the_semver() -> None:
    derived = derive_deployment(
        _minimal(ttl={"max_ttl_seconds": 7200, "product_ttl_seconds": 3600}, door=_door())
    )
    by_key = {entry.key: entry for entry in derived.manifest.artifacts}
    for key, class_id in (("ttl", TTL_BINDING.class_id), ("door", EGRESS_DOOR.class_id)):
        assert (by_key[key].class_id, by_key[key].role, by_key[key].registration) == (class_id, "register", "typed")
        assert derived.documents[key]["semver"] == "1.0.0"
    assert isinstance(parse_artifact(derived.documents["ttl"], TTL_BINDING), TtlBinding)
    assert isinstance(parse_artifact(derived.documents["door"], EGRESS_DOOR), EgressDoorBinding)
    assert derived.keys.ttl == "ttl" and derived.keys.door == "door"


def test_a_config_declaring_neither_section_derives_what_it_derived_before() -> None:
    before = derive_deployment(_minimal())
    assert before.keys.ttl is None and before.keys.door is None and before.keys.agent is None
    assert [entry.key for entry in before.manifest.artifacts] == ["product_class", "resolution", "policy"]


@pytest.mark.parametrize("key", ["principal_id", "role", "issuer_url", "credential"])
def test_a_value_with_another_home_is_refused_under_door_by_name(key: str) -> None:
    with pytest.raises(ValueError, match=key):
        derive_deployment(_minimal(door=_door(**{key: "x"})))


def test_a_door_asserting_another_tenant_is_refused_at_derivation() -> None:
    """R-6 — declared, and held to the deployment's one tenant."""
    with pytest.raises(ValueError, match="producer_tenant 'somebody-else'"):
        derive_deployment(_minimal(door=_door(producer_tenant="somebody-else")))


def test_a_ttl_window_that_is_not_positive_is_refused() -> None:
    with pytest.raises(ValueError, match="positive"):
        derive_deployment(_minimal(ttl={"max_ttl_seconds": 0, "product_ttl_seconds": 3600}))


def test_a_third_ttl_key_is_refused_as_documentation_not_control() -> None:
    with pytest.raises(ValueError, match="ttl_anchor_basis"):
        derive_deployment(
            _minimal(ttl={"max_ttl_seconds": 1, "product_ttl_seconds": 1, "ttl_anchor_basis": "latest"})
        )


# --- 3. the versioned agent section (R-2) ---------------------------------------


def test_the_agent_section_derives_on_the_versioned_path_with_no_semver_injected() -> None:
    derived = derive_deployment(_minimal(agent=_agent()))
    entry = next(entry for entry in derived.manifest.artifacts if entry.key == "agent")
    assert (entry.class_id, entry.role, entry.registration) == ("ccf.agent-definition", "register", "versioned")
    document = derived.documents["agent"]
    assert "semver" not in document
    assert document["tenant"] == TENANT, "the deployment's tenant is filled, never restated"
    assert derived.keys.agent == "agent"
    assert derived.manifest.artifacts[-1].key == "agent", "appended last, so earlier key orders hold"


def test_an_agent_declaring_another_tenant_is_refused_and_the_same_tenant_is_admitted() -> None:
    with pytest.raises(ValueError, match="declares tenant 'other'"):
        derive_deployment(_minimal(agent=_agent(tenant="other")))
    derived = derive_deployment(_minimal(agent=_agent(tenant=TENANT)))
    assert derived.documents["agent"]["tenant"] == TENANT


@pytest.mark.parametrize("fixed", ["class_id", "role", "registration"])
def test_the_agent_sections_fixed_bookkeeping_cannot_be_overridden(fixed: str) -> None:
    with pytest.raises(ValueError, match=fixed):
        derive_deployment(_minimal(agent=_agent(**{fixed: "x"})))


def test_a_malformed_agent_is_refused_at_derivation_not_boot() -> None:
    with pytest.raises(Exception, match="archetype"):
        derive_deployment(_minimal(agent=_agent(archetypes=["no-such-archetype"])))


# --- 4. the keys -------------------------------------------------------------------


def test_the_keys_name_every_section_and_honor_a_key_override() -> None:
    derived = derive_deployment(
        _minimal(
            ttl={"key": "windows", "max_ttl_seconds": 2, "product_ttl_seconds": 1},
            replay={"record_class": "ccf.replay-record", "query_pin_class": "ccf.graph-query", "store_dirname": "s"},
        )
    )
    keys = derived.keys
    assert keys.product_class == "product_class"
    assert keys.policy_bundle == "policy" and keys.resolution_spec == "resolution"
    assert keys.request_contract is None and keys.half_life is None and keys.debt_profile is None
    assert keys.replay == "replay" and keys.ttl == "windows" and keys.door is None
    assert keys.operator_parameters == () and keys.producers == () and keys.policy_constraints == ()


# --- 5. the environment document ------------------------------------------------------


def _environment_text(**overrides: str) -> str:
    lines = [
        "config: ccf_config.yaml",
        "substrate: {setting: database_path, prefix: fixture, suffix: .db}",
        "sources:",
        "  store:",
        "    dsn: {from_env: FIXTURE_DSN, remedy: 'export FIXTURE_DSN with a read-only DSN'}",
    ]
    lines.extend(overrides.values())
    return "\n".join(lines) + "\n"


def test_the_environment_document_loads_and_resolves_every_name_at_once(tmp_path: pathlib.Path) -> None:
    (tmp_path / ENVIRONMENT_DOCUMENT_NAME).write_text(_environment_text(), encoding="utf-8")
    document = load_environment_document(tmp_path)
    assert isinstance(document, EnvironmentDocument)
    assert document.substrate.setting == "database_path"
    assert resolve_values(document.sources, {"FIXTURE_DSN": "postgresql://x"}) == {"store": {"dsn": "postgresql://x"}}
    with pytest.raises(EnvironmentMissing, match="export FIXTURE_DSN"):
        resolve_values(document.sources, {})


@pytest.mark.parametrize(
    "line",
    [
        "    literal: {from_env: 'https://a.b/c', remedy: 'x'}",  # a value where a name belongs
        "    dsn2: {from_env: FIXTURE_DSN, remedy: ''}",  # an empty remedy
    ],
)
def test_a_value_or_a_blank_remedy_where_a_name_belongs_is_refused(tmp_path: pathlib.Path, line: str) -> None:
    (tmp_path / ENVIRONMENT_DOCUMENT_NAME).write_text(_environment_text(extra=line), encoding="utf-8")
    with pytest.raises(ValueError):
        load_environment_document(tmp_path)


def test_a_control_plane_value_in_the_environment_is_refused_by_name(tmp_path: pathlib.Path) -> None:
    (tmp_path / ENVIRONMENT_DOCUMENT_NAME).write_text(
        _environment_text() + "door:\n  principal_id: PRIN-1\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="principal_id"):
        load_environment_document(tmp_path)


def test_an_absent_environment_document_is_refused_with_its_name(tmp_path: pathlib.Path) -> None:
    with pytest.raises(FileNotFoundError, match=ENVIRONMENT_DOCUMENT_NAME):
        load_environment_document(tmp_path)
