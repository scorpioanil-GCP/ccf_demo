"""The four-type skill catalog — schema, registration, discovery (AGNT-03).

Written before the implementation per the TDD discipline (D-IMPL-12,
D-IMPL-29, D-05, D-08). The claims pinned here:

* ``SkillCatalogEntry`` validates for each of the four D-IMPL-12 skill types
  — ``local_callable``, ``tool``, ``mcp``, ``peering`` — with two-field
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
    ProcedureBinding,
    SkillArgumentProperty,
    SkillArgumentSchema,
    SkillCatalog,
    SkillCatalogEntry,
    SkillNotInCatalog,
    SkillRequirements,
    skill_catalog_key,
)
from tests.composition import register_skill_entry

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking" / "skills"


def _fixture(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / name).read_text())
    return loaded


def _tool_fixture() -> dict[str, Any]:
    return _fixture("covenant_metrics_tool.yaml")


def _mcp_fixture() -> dict[str, Any]:
    return _fixture("document_fetch_mcp.yaml")


def _peering_fixture() -> dict[str, Any]:
    return _fixture("remote_products_peering.yaml")


def _mcp_product_fixture() -> dict[str, Any]:
    return _fixture("exposure_rollup_mcp_product.yaml")


def _all_entry_documents() -> list[dict[str, Any]]:
    tool = _tool_fixture()
    return [
        tool["entry"],
        _mcp_fixture()["entry"],
        _mcp_product_fixture()["entry"],
        *tool["variants"].values(),
    ]


class TestEntrySchema:
    def test_all_six_skill_types_validate(self) -> None:
        """Five D-IMPL-12/56 types plus `mcp_product` (`D-IMPL-340`, ruling 5).

        The count is pinned so the vocabulary grows only by a ruling: the
        sixth member was added under Dave's ruling that `mcp_product` ships as
        its own skill type rather than as a second reading of `mcp`.
        """
        documents = _all_entry_documents()
        entries = [SkillCatalogEntry.model_validate(d) for d in documents]
        assert {e.skill_type for e in entries} == SKILL_TYPES
        assert len(SKILL_TYPES) == 6

    def test_an_mcp_product_entry_must_produce_what_it_asks_for(self) -> None:
        """`D-IMPL-340`: `produces` and the binding's class are one statement."""
        fixture = _mcp_product_fixture()
        document = dict(fixture["entry"])
        document["binding"] = dict(fixture["disagreeing_binding"])
        with pytest.raises(ValueError, match="asks its producer for"):
            SkillCatalogEntry.model_validate(document)

    def test_a_seventh_skill_type_is_refused(self) -> None:
        document = dict(_tool_fixture()["entry"])
        document["skill_type"] = document["name"]  # any non-member value
        with pytest.raises(ValueError):
            SkillCatalogEntry.model_validate(document)

    def test_the_retired_a2a_token_is_refused_by_name(self) -> None:
        """A grant under the old token is not silently reinterpreted (T-06-106).

        D-IMPL-59 part 1 renamed the skill type token ``a2a`` to ``peering``.
        The retired member is *removed*, so an artifact still declaring it hits
        the same closed-world refusal an entirely unknown type hits — it is not
        aliased, defaulted, or migrated. Reinterpreting such an entry as
        ``peering`` would mean honouring a capability grant whose recorded token
        no longer exists, which is a governance failure rather than a migration
        convenience.

        What would fail here: adding ``a2a`` back as an alias of ``peering``, or
        widening ``SkillType`` to tolerate it for backwards compatibility. The
        message check is what distinguishes refused-by-name from refused-by-
        accident: the error must enumerate the members that *do* exist.
        """
        retired = _peering_fixture()["retired_token"]
        assert retired["token"] not in SKILL_TYPES
        with pytest.raises(ValueError) as excinfo:
            SkillCatalogEntry.model_validate(retired["entry"])
        message = str(excinfo.value)
        # SEC-024 (choice C, `D-IMPL-371`): `CCFContract` hides rejected input
        # values from error text, so the retired token itself is no longer
        # echoed. Refused-by-name is read from the structured error instead:
        # a closed-world literal refusal on `skill_type`.
        errors = excinfo.value.errors()  # type: ignore[attr-defined]
        assert [(e["type"], tuple(e["loc"])) for e in errors] == [
            ("literal_error", ("skill_type",))
        ]
        assert retired["token"] not in message
        # Refused against the enumerated closed world, naming the surviving
        # member the deployment should have re-declared under.
        assert "peering" in message

    def test_an_entry_without_a_description_is_refused(self) -> None:
        """D-IMPL-56 / D-16: `description` is required — no default, no sentinel.

        A skill's description is the deployment's statement of what the skill
        is for. An entry that omits it is malformed, not merely terse: three
        adapters independently inventing a description is exactly the
        divergence D-17 exists to prevent, so the artifact must carry it.
        """
        document = dict(_tool_fixture()["entry"])
        document.pop("description", None)
        with pytest.raises(ValueError):
            SkillCatalogEntry.model_validate(document)

    def test_an_entry_without_an_argument_schema_is_refused(self) -> None:
        """D-IMPL-56: `argument_schema` is required on every entry."""
        document = dict(_tool_fixture()["entry"])
        document.pop("argument_schema", None)
        with pytest.raises(ValueError):
            SkillCatalogEntry.model_validate(document)

    def test_argument_schema_is_typed_and_closed_world(self) -> None:
        entry = SkillCatalogEntry.model_validate(_tool_fixture()["entry"])
        assert isinstance(entry.argument_schema, SkillArgumentSchema)
        for spec in entry.argument_schema.properties.values():
            assert isinstance(spec, SkillArgumentProperty)
        with pytest.raises(ValueError):
            SkillArgumentSchema.model_validate(
                {"properties": {}, "required": [], "unexpected": True}
            )

    def test_a_required_name_absent_from_properties_is_refused(self) -> None:
        document = dict(_tool_fixture()["entry"])
        schema = dict(document["argument_schema"])
        schema["required"] = [*schema.get("required", []), document["name"]]
        with pytest.raises(ValueError):
            SkillArgumentSchema.model_validate(schema)

    def test_a_property_without_a_description_is_refused(self) -> None:
        """Same D-16 forcing function as the entry description."""
        with pytest.raises(ValueError):
            SkillArgumentProperty.model_validate({"type": "string"})

    def test_a_property_with_a_non_json_type_is_refused(self) -> None:
        document = dict(_tool_fixture()["entry"])
        with pytest.raises(ValueError):
            SkillArgumentProperty.model_validate(
                {"type": document["name"], "description": document["name"]}
            )

    def test_argument_schema_renders_as_an_mcp_input_schema(self) -> None:
        """Lossless render: type object, properties, required, closed world."""
        entry = SkillCatalogEntry.model_validate(_tool_fixture()["entry"])
        rendered = entry.argument_schema.to_input_schema()
        assert rendered["type"] == "object"
        assert rendered["additionalProperties"] is False
        assert set(rendered["properties"]) == set(
            entry.argument_schema.properties
        )
        for name, spec in entry.argument_schema.properties.items():
            assert rendered["properties"][name] == {
                "type": spec.type,
                "description": spec.description,
            }
        assert tuple(rendered["required"]) == entry.argument_schema.required

    def test_a_procedure_entry_validates_with_the_procedure_binding(self) -> None:
        """The fifth skill type (D-IMPL-56): instruction travels on seam 1.

        A `procedure` skill's content is an `InstructionBinding` reference —
        a pinned prompt-artifact URI, never inline text — consumed on seam 1
        (context injection) only. A `procedure` entry carrying any other
        binding block is refused by the same agreement validator every other
        type answers to (T-07-05).
        """
        tool = _tool_fixture()
        entry = SkillCatalogEntry.model_validate(tool["variants"]["procedure"])
        assert entry.skill_type == "procedure"
        assert isinstance(entry.binding, ProcedureBinding)
        mismatched = dict(tool["variants"]["procedure"])
        mismatched["binding"] = dict(tool["entry"]["binding"])
        with pytest.raises(ValueError):
            SkillCatalogEntry.model_validate(mismatched)

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
        version = register_skill_entry(catalog, control_plane, entry)
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
        register_skill_entry(catalog, control_plane, entry)
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
        refusal = register_skill_entry(catalog, control_plane, mutant)
        assert isinstance(refusal, RefuseUnbumpedChange)
        # Nothing new stored under the key.
        assert len(control_plane.versions(skill_catalog_key(entry))) == 1

    def test_both_banking_fixtures_register(self) -> None:
        registry = ControlPlaneRegistry()
        catalog = SkillCatalog(registry)
        for document in (_tool_fixture()["entry"], _mcp_fixture()["entry"]):
            entry = SkillCatalogEntry.model_validate(document)
            assert isinstance(register_skill_entry(catalog, registry, entry), str)

    def test_mcp_and_peering_entries_register_without_dispatch(self) -> None:
        # D-08: the schema covers all four types now; no transport exists yet.
        registry = ControlPlaneRegistry()
        catalog = SkillCatalog(registry)
        tool = _tool_fixture()
        for document in (_mcp_fixture()["entry"], tool["variants"]["peering"]):
            entry = SkillCatalogEntry.model_validate(document)
            assert isinstance(register_skill_entry(catalog, registry, entry), str)


class TestDiscovery:
    def _populated(self) -> tuple[SkillCatalog, list[SkillCatalogEntry]]:
        registry = ControlPlaneRegistry()
        catalog = SkillCatalog(registry)
        entries = [
            SkillCatalogEntry.model_validate(d) for d in _all_entry_documents()
        ]
        for entry in entries:
            register_skill_entry(catalog, registry, entry)
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
            assert isinstance(register_skill_entry(first, registry, entry), str)
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

    def test_resolution_audits_only_the_entry_actually_returned(self) -> None:
        """WR-03: the declared-version search probes unaudited.

        Pinned resolution has to examine every content under the key to find
        the one whose declared version matches. Auditing each probe as a
        `resolve` would record reads of artifacts no caller ever received —
        and every grant request and every BoundSkillView access comes through
        here, so the audit plane would fill with phantom reads. One audited
        resolution per successful call: the entry returned (the WR-08
        discipline, applied to its sibling path).
        """
        registry = ControlPlaneRegistry()
        catalog = SkillCatalog(registry)
        fixture = _tool_fixture()
        first = SkillCatalogEntry.model_validate(fixture["entry"])
        assert isinstance(register_skill_entry(catalog, registry, first), str)
        major, minor, patch = (
            int(part) for part in first.artifact_version.split(".")
        )
        second = first.model_copy(
            update={
                "artifact_version": f"{major}.{minor}.{patch + 1}",
                "requirements": SkillRequirements(
                    required_scopes=first.requirements.required_scopes
                    | {fixture["mutation"]["extra_scope"]},
                    required_context_products=(
                        first.requirements.required_context_products
                    ),
                ),
            }
        )
        assert isinstance(register_skill_entry(catalog, registry, second), str)
        key = skill_catalog_key(first)
        assert len(registry.versions(key)) == 2

        before = len(registry.audit_events())
        assert catalog.resolve(second.tenant, second.name, second.artifact_version) == (
            second
        )
        resolutions = [
            event
            for event in registry.audit_events()[before:]
            if event.action == "resolve"
        ]
        assert len(resolutions) == 1
        assert resolutions[0].key == key
        assert resolutions[0].version == content_hash(second)

    def test_resolving_an_unknown_version_raises(self) -> None:
        catalog, entries = self._populated()
        entry = entries[0]
        with pytest.raises(SkillNotInCatalog):
            catalog.resolve(entry.tenant, entry.name, entry.schema_version + "-x")


class TestCapability:
    """D-IMPL-353 §1.2 / §1.5f: `register` takes the capability for exactly the entry's key."""

    def test_a_capability_for_another_key_is_refused_before_anything_is_registered(self) -> None:
        from tests.composition import composition_register

        registry = ControlPlaneRegistry()
        catalog = SkillCatalog(registry)
        entry = SkillCatalogEntry.model_validate(_tool_fixture()["entry"])
        other = f"{entry.tenant}/{SKILL_CATALOG_ENTRY.class_id}/not-this-entry"
        # The catalog refuses the disagreement itself, typed, before the
        # registry is touched (J-RUNTIME's shape, taken verbatim at the join).
        with pytest.raises(ValueError, match="minted for"):
            catalog.register(composition_register(registry, other), entry)
        assert registry.versions(skill_catalog_key(entry)) == ()
        assert registry.versions(other) == ()
        assert "register_versioned" not in {e.action for e in registry.audit_events()}

    def test_the_door_kind_and_the_composition_kind_both_register_and_a_fabrication_dies(self) -> None:
        from ccf.authz.capability import CapabilityBypassError, Register, SkillCatalogRegister

        from tests.controlplane.capabilities import fabrications, register_capability

        registry = ControlPlaneRegistry()
        catalog = SkillCatalog(registry)
        entry = SkillCatalogEntry.model_validate(_tool_fixture()["entry"])
        key = skill_catalog_key(entry)
        # A forgery carrying the right `resource` reaches the registry and dies
        # at its `verify_any`; one carrying no `resource` at all dies at the
        # catalog's own key check. Either way: a typed refusal, nothing filed.
        for label, forged in fabrications(SkillCatalogRegister, tenant=entry.tenant, resource=key):
            with pytest.raises((CapabilityBypassError, ValueError)):
                catalog.register(forged, entry)  # type: ignore[arg-type]
            assert registry.versions(key) == (), label
        assert isinstance(catalog.register(register_capability(key, SkillCatalogRegister), entry), str)
        bumped = entry.model_copy(update={"artifact_version": "9.9.9", "description": "bumped"})
        assert isinstance(catalog.register(register_capability(key, Register), bumped), str)
        assert len(registry.versions(key)) == 2
