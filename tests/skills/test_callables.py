"""The CallableRegistry — the D-19 control on artifact-driven code execution.

What this suite holds ``src/ccf/skills/callables.py`` and the dispatch path
that resolves through it to:

* a duplicate key is fatal at registration, never last-writer-wins;
* an unregistered key raises ``CallableNotRegistered`` — and nothing is
  imported on the way to that answer;
* **the hostile-entry case**: a catalog entry whose ``callable_ref`` is the
  literal string a hostile third-party artifact source might ship resolves to
  no registered key. It is refused because nothing registered it, not because
  a denylist recognized it — the SDK ships no denylist and no name-shaped
  judgement at all;
* **the multi-principal case (D-23)**: two composition roots binding the same
  key to different callables each get their own, so a registry is not an
  ambient process-wide namespace one deployment can shadow for another.

Every key, ref, and expected output is a fixture value in
``tests/fixtures/banking/skills/covenant_metrics_tool.yaml`` (§6.4); this
module holds the mechanism assertions and no vocabulary of its own.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.controlplane.artifacts import parse_artifact
from ccf.skills.callables import (
    CallableNotRegistered,
    CallableRegistry,
    DuplicateCallableKey,
)
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalogEntry
from ccf.skills.dispatch import SkillInvocation, dispatch_skill

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "skills"


def _fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "covenant_metrics_tool.yaml").read_text()
    )
    return loaded


def _values() -> dict[str, Any]:
    values: dict[str, Any] = _fixture()["callables"]
    return values


def _entry(document: dict[str, Any]) -> SkillCatalogEntry:
    parsed = parse_artifact(document, SKILL_CATALOG_ENTRY)
    assert isinstance(parsed, SkillCatalogEntry)
    return parsed


def _constant(value: str) -> Any:
    """A deterministic callable tagged with ``value`` — mechanism, not a fixture."""

    def _call(arguments: Mapping[str, str]) -> dict[str, str]:
        return {"registry": value, **arguments}

    return _call


def test_registering_one_key_twice_is_fatal_at_registration() -> None:
    """Append-only, like the Control Plane it mirrors: two callables under one
    key means every entry naming it is ambiguous."""
    values = _values()
    registry = CallableRegistry()
    registry.register(values["registered_key"], _constant(values["registered_key"]))
    with pytest.raises(DuplicateCallableKey) as excinfo:
        registry.register(values["registered_key"], _constant(values["registered_key"]))
    assert values["registered_key"] in str(excinfo.value)
    assert len(registry) == 1


def test_an_unregistered_key_resolves_to_nothing() -> None:
    values = _values()
    registry = CallableRegistry()
    with pytest.raises(CallableNotRegistered):
        registry.resolve(values["registered_key"])
    assert values["registered_key"] not in registry
    assert registry.keys() == ()


def test_a_third_party_catalog_entry_naming_os_system_resolves_to_nothing(
    callable_registry: CallableRegistry,
) -> None:
    """The D-19 property, stated as a test.

    The entry is structurally valid and would be admissible from any artifact
    source, including an MCP artifact store or an A2A peer. Dispatch still
    refuses it, because its ``callable_ref`` is a key the composition root did
    not register — and no module is imported to find that out. The refusal
    does not depend on the SDK recognizing the name.
    """
    values = _values()
    hostile = _entry(values["hostile_entry"])
    modules_before = set(sys.modules)

    with pytest.raises(CallableNotRegistered) as excinfo:
        dispatch_skill(
            hostile,
            arguments=_fixture()["dispatch"]["arguments"],
            callable_registry=callable_registry,
        )

    assert hostile.binding.callable_ref in str(excinfo.value)
    # Nothing was imported on the way to the refusal: the resolution is a
    # dictionary miss, not an import that happened to fail.
    assert set(sys.modules) == modules_before


def test_the_refusal_is_absence_not_a_denylist(
    callable_registry: CallableRegistry,
) -> None:
    """The hostile ref is refused by the same mechanism as any other unknown
    key: the SDK ships no denylist, so there is nothing to bypass."""
    values = _values()
    hostile_ref = values["hostile_entry"]["binding"]["callable_ref"]
    unremarkable_ref = values["multi_principal"]["shared_key"] + "-absent"
    for ref in (hostile_ref, unremarkable_ref):
        with pytest.raises(CallableNotRegistered):
            callable_registry.resolve(ref)


def test_two_composition_roots_binding_one_key_cannot_shadow_each_other() -> None:
    """D-23: a registry is an object a composition root holds, not an ambient
    namespace. Two deployments in one process each resolve their own."""
    values = _values()["multi_principal"]
    first = CallableRegistry()
    second = CallableRegistry()
    first.register(values["shared_key"], _constant(values["first_output"]))
    second.register(values["shared_key"], _constant(values["second_output"]))

    entry = _entry(_fixture()["variants"]["local_callable"])
    arguments = _fixture()["dispatch"]["arguments"]

    first_result = dispatch_skill(entry, arguments=arguments, callable_registry=first)
    second_result = dispatch_skill(entry, arguments=arguments, callable_registry=second)

    assert isinstance(first_result, SkillInvocation)
    assert isinstance(second_result, SkillInvocation)
    assert first_result.output["registry"] == values["first_output"]
    assert second_result.output["registry"] == values["second_output"]
    # Neither registration is observable from the other registry: registering
    # the same key twice within one root is fatal, but across two roots it is
    # simply two independent bindings.
    assert first.resolve(values["shared_key"]) is not second.resolve(
        values["shared_key"]
    )
