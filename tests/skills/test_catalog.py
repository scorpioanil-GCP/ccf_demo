"""The four-type skill catalog — schema, registration, discovery (AGNT-03).

Written before the implementation per the TDD discipline (D-IMPL-12,
D-IMPL-29, D-05, D-08). The claims pinned here:

* ``SkillCatalogEntry`` validates for each of the four D-IMPL-12 skill types
  — ``local_callable``, ``tool``, ``mcp``, ``a2a`` — with two-field
  D-IMPL-28 versioning, a per-type typed binding block, and a typed
  requirements declaration whose members are frozensets of opaque
  identifiers. A fifth type is refused; a binding that disagrees with the
  declared type is refused; extra fields are refused (closed world).
* Registration flows through the D-05 hash-verified versioned Control Plane
  path (``register_versioned``): an unbumped content change is a returned
  ``RefuseUnbumpedChange``, and every registration lands in the audit log.
* Discovery lists entries by skill type; pinned resolution returns the exact
  registered entry by declared ``artifact_version`` or by content hash.

Every entry in this module is loaded **from the banking skill fixtures**
(CLAUDE.md §6.4); mutants are structural transformations of fixture-loaded
data, never inline documents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry, RefuseUnbumpedChange
from ccf.skills.catalog import (
    SKILL_CATALOG_ENTRY,
    SKILL_TYPES,
    SkillCatalog,
    SkillCatalogEntry,
    SkillNotInCatalog,
    SkillRequirements,
    skill_catalog_key,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking" / "skills"


def _fixture(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / name).read_text())
    return loaded


def _tool_fixture() -> dict[str, Any]:
    return _fixture("covenant_metrics_tool.yaml")


def _mcp_fixture() -> dict[str, Any]:
    return _fixture("document_fetch_mcp.yaml")


def _all_entry_documents() -> list[dict[str, Any]]:
    tool = _tool_fixture()
    return [
        tool["entry"],
        _mcp_fixture()["entry"],
        *tool["variants"].values(),
    ]


class TestEntrySchema:
    def test_all_four_skill_types_validate(self) -> None:
        documents = _all_entry_documents()
        entries = [SkillCatalogEntry.model_validate(d) for d in documents]
        assert {e.skill_type for e in entries} == SKILL_TYPES
        assert len(SKILL_TYPES) == 4

    def test_a_fifth_skill_type_is_refused(self) -> None:
        document = dict(_tool_fixture()["entry"])
        document["skill_type"] = document["name"]  # any non-member value
        with pytest.raises(ValueError):
            SkillCatalogEntry.model_validate(document)

    def test_a_binding_disagreeing_with_the_type_is_refused(self) -> None:
        tool = _tool_fixture()["entry"]
        mcp = _mcp_fixture()["entry"]
        document = dict(tool)
        document["binding"] = mcp["binding"]
        with pytest.raises(ValueError):
            SkillCatalogEntry.model_validate(document)

    def test_extra_fields_are_refused(self) -> None:
        document = dict(_mcp_fixture()["entry"])
        document["unexpected"] = document["name"]
        with pytest.raises(ValueError):
            SkillCatalogEntry.model_validate(document)

    def test_versions_must_be_semver(self) -> None:
        document = dict(_tool_fixture()["entry"])
        document["artifact_version"] = document["name"]
        with pytest.raises(ValueError):
            SkillCatalogEntry.model_validate(document)

    def test_requirements_are_frozensets_of_opaque_identifiers(self) -> None:
        entry = SkillCatalogEntry.model_validate(_tool_fixture()["entry"])
        assert isinstance(entry.requirements, SkillRequirements)
        assert isinstance(entry.requirements.required_scopes, frozenset)
        assert isinstance(entry.requirements.required_context_products, frozenset)

    def test_an_empty_requirement_set_is_an_explicit_statement(self) -> None:
        entry = SkillCatalogEntry.model_validate(_mcp_fixture()["entry"])
        assert entry.requirements.required_context_products == frozenset()

    def test_the_artifact_class_is_declared(self) -> None:
        assert SKILL_CATALOG_ENTRY.class_id == "ccf.skill-catalog-entry"
        assert SKILL_CATALOG_ENTRY.contract is SkillCatalogEntry


class TestRegistration:
    def test_registration_goes_through_the_versioned_path(self) -> None:
        control_plane = ControlPlaneRegistry()
        catalog = SkillCatalog(control_plane)
        entry = SkillCatalogEntry.model_validate(_tool_fixture()["entry"])
        version = catalog.register(entry)
        assert version == content_hash(entry)
        key = skill_catalog_key(entry)
        assert control_plane.versions(key) == (version,)
        assert control_plane.artifact_class_of(key) == SKILL_CATALOG_ENTRY.class_id
        actions = [e.action for e in control_plane.audit_events()]
        assert "register_versioned" in actions

    def test_an_unbumped_content_change_is_refused(self) -> None:
        control_plane = ControlPlaneRegistry()
        catalog = SkillCatalog(control_plane)
        fixture = _tool_fixture()
        entry = SkillCatalogEntry.model_validate(fixture["entry"])
        catalog.register(entry)
        mutant = entry.model_copy(
            update={
                "requirements": SkillRequirements(
                    required_scopes=entry.requirements.required_scopes
                    | {fixture["mutation"]["extra_scope"]},
                    required_context_products=(
                        entry.requirements.required_context_products
                    ),
                )
            }
        )
        refusal = catalog.register(mutant)
        assert isinstance(refusal, RefuseUnbumpedChange)
        # Nothing new stored under the key.
        assert len(control_plane.versions(skill_catalog_key(entry))) == 1

    def test_both_banking_fixtures_register(self) -> None:
        catalog = SkillCatalog(ControlPlaneRegistry())
        for document in (_tool_fixture()["entry"], _mcp_fixture()["entry"]):
            entry = SkillCatalogEntry.model_validate(document)
            assert isinstance(catalog.register(entry), str)

    def test_mcp_and_a2a_entries_register_without_dispatch(self) -> None:
        # D-08: the schema covers all four types now; no transport exists yet.
        catalog = SkillCatalog(ControlPlaneRegistry())
        tool = _tool_fixture()
        for document in (_mcp_fixture()["entry"], tool["variants"]["a2a"]):
            entry = SkillCatalogEntry.model_validate(document)
            assert isinstance(catalog.register(entry), str)


class TestDiscovery:
    def _populated(self) -> tuple[SkillCatalog, list[SkillCatalogEntry]]:
        catalog = SkillCatalog(ControlPlaneRegistry())
        entries = [
            SkillCatalogEntry.model_validate(d) for d in _all_entry_documents()
        ]
        for entry in entries:
            catalog.register(entry)
        return catalog, entries

    def test_discovery_lists_all_registered_entries(self) -> None:
        catalog, entries = self._populated()
        assert set(catalog.discover()) == set(entries)

    def test_discovery_filters_by_skill_type(self) -> None:
        catalog, entries = self._populated()
        for skill_type in SKILL_TYPES:
            expected = {e for e in entries if e.skill_type == skill_type}
            assert set(catalog.discover(skill_type=skill_type)) == expected

    def test_a_second_catalog_over_the_same_registry_discovers_everything(
        self,
    ) -> None:
        """Discovery derives from registry state, never an instance index.

        IN-03: a second catalog constructed over the same registry — or the
        same catalog after a process restart — must discover exactly the
        entries registered through the first, because the registry is the
        single store and the catalog keeps no volatile membership of its own.
        """
        registry = ControlPlaneRegistry()
        first = SkillCatalog(registry)
        entries = [
            SkillCatalogEntry.model_validate(d) for d in _all_entry_documents()
        ]
        for entry in entries:
            assert isinstance(first.register(entry), str)
        second = SkillCatalog(registry)
        assert set(second.discover()) == set(entries)
        assert set(second.discover()) == set(first.discover())

    def test_pinned_resolution_by_artifact_version(self) -> None:
        catalog, entries = self._populated()
        entry = entries[0]
        resolved = catalog.resolve(
            entry.tenant, entry.name, entry.artifact_version
        )
        assert resolved == entry

    def test_pinned_resolution_by_content_hash(self) -> None:
        catalog, entries = self._populated()
        entry = entries[0]
        assert catalog.resolve(entry.tenant, entry.name, content_hash(entry)) == entry

    def test_resolving_an_unregistered_skill_raises(self) -> None:
        catalog, entries = self._populated()
        entry = entries[0]
        with pytest.raises(SkillNotInCatalog):
            catalog.resolve(entry.tenant, entry.tenant, entry.artifact_version)

    def test_resolving_an_unknown_version_raises(self) -> None:
        catalog, entries = self._populated()
        entry = entries[0]
        with pytest.raises(SkillNotInCatalog):
            catalog.resolve(entry.tenant, entry.name, entry.schema_version + "-x")
