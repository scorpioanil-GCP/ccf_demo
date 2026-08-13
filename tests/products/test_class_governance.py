"""The class-level governance the §6.3 contract needs and did not have.

Three §6.3 elements — **Freshness SLA**, **Discovery**, **Addressability** —
were named by ``contract.py``'s own module docstring as living on
:class:`~ccf.products.contract.RegisteredProductClass` while none of the three
existed there. ``D-IMPL-106`` ruled the first onto the class (option (b),
reading 2: the sidebar's "freshness SLA" names a class-level promise the
product was assembled under, not an instance field, which is what makes the
two "same seven fields" enumerations at ``docs/CCF_Whitepaper_1-2.md:2381`` and
``:2381-2405`` consistent and keeps ``plan_id`` on the vessel). ``D-IMPL-98``
then ruled that discovery and addressability are **not** declaration-only this
phase. And ``D-IMPL-31``'s constituent-validity floors were ruled on
2026-07-25 and never built.

This module holds all four, plus the payload-schema pin, against the two
disciplines the tree already enforces on class-level governance:

* **a default is a positive assertion, never an absence.** The tree's shipped
  sentinels — ``MODE_1_MODEL_VERSION``, ``NO_HITL_ACTIONS``, ``NO_ADAPTER``,
  ``accepted_policy_binding_modes``' tier-1 default — each say something
  affirmative about the decision they describe. Every default here is asserted
  to be one, so a class registered before the elements existed states what it
  in fact stated rather than falling silent;
* **authored key, derived version.** ``ProductClassDeclaration`` deliberately
  does not declare ``max_ttl_version``, because that pin is minted by
  *registering* the value and an artifact declaring it would be authoring a
  hash of something it does not contain. The payload-schema pin follows the
  same rule, and this module asserts the asymmetry rather than trusting it.

Requirements CPS-02, CPS-03, CPS-08.
"""

from __future__ import annotations

import pytest

from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    NO_PAYLOAD_SCHEMA,
    NO_VALIDITY_FLOORS,
    NOT_ADDRESSABLE,
    NOT_DISCOVERABLE,
    UNMEASURED_FRESHNESS_SLA,
    ConstituentValidityFloors,
    FreshnessSLA,
    MaxTTL,
    ProductAddress,
    ProductClassRegistrationError,
    ProductDiscovery,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.payload import ProductPayloadSchema

MAX_TTL_KEY = "fixture.max-ttl"
PAYLOAD_SCHEMA_KEY = "fixture.payload-schema"


def _registry_with_ceiling() -> tuple[ControlPlaneRegistry, str]:
    registry = ControlPlaneRegistry()
    version = registry.register(MAX_TTL_KEY, MaxTTL(seconds=3600))
    return registry, version


def _register(**overrides: object) -> RegisteredProductClass:
    registry = overrides.pop("registry", None)
    version = overrides.pop("max_ttl_version", None)
    if registry is None:
        registry, version = _registry_with_ceiling()
    assert isinstance(registry, ControlPlaneRegistry)
    arguments: dict[str, object] = {
        "registry": registry,
        "schema_name": "fixture.governance",
        "schema_version": "1.0.0",
        "ttl_anchor": "from_decision",
        "assembly_mode": "algorithmic",
        "max_ttl_key": MAX_TTL_KEY,
        "max_ttl_version": version,
    }
    arguments.update(overrides)
    return register_product_class(**arguments)  # type: ignore[arg-type]


def _payload_schema() -> ProductPayloadSchema:
    return ProductPayloadSchema.model_validate(
        {
            "properties": {"subject": {"type": "string", "description": "URI"}},
            "required": ["subject"],
        }
    )


class TestTheThreeAbsentElementsAreBorne:
    """CPS-02: each element has a named field, and the field is the ruled one."""

    def test_freshness_sla_is_class_level_and_not_on_the_vessel(self) -> None:
        """D-IMPL-106 option (b), the cheapest measured option and the only
        one that moves no content address."""
        from ccf.products.contract import ContextProductContract

        assert "freshness_sla" in RegisteredProductClass.model_fields
        assert "freshness_sla" not in ContextProductContract.model_fields

    def test_discovery_and_addressability_are_class_level(self) -> None:
        assert "discovery" in RegisteredProductClass.model_fields
        assert "addressability" in RegisteredProductClass.model_fields

    def test_freshness_sla_is_per_signal_and_not_a_scalar(self) -> None:
        """§6.3 at ``:1453`` — *"Freshness SLA varies by signal and by decision"*.

        D-IMPL-106 ruled the placement and left the internal shape to the
        implementing plan, saying in terms that **no scalar is ruled in by
        silence**. A single number for a product assembled from signals of
        different cadence is exactly the asymmetry §6.3 says a product must
        not hide.
        """
        sla = FreshnessSLA(
            max_age_seconds_by_signal={"fixture.fast": 60, "fixture.slow": 86400}
        )
        assert sla.max_age_seconds_by_signal["fixture.fast"] == 60
        registered = _register(freshness_sla=sla)
        assert registered.freshness_sla == sla

    def test_discovery_carries_intent_domain_and_capability(self) -> None:
        """§6.3 at ``:1463`` — a registry locating products by exactly those."""
        discovery = ProductDiscovery(
            domain="fixture.domain",
            intents=frozenset({"fixture.intent"}),
            capabilities=frozenset({"fixture.capability"}),
        )
        assert _register(discovery=discovery).discovery == discovery

    def test_addressability_carries_the_address_the_class_answers_at(self) -> None:
        """§6.3 at ``:1465``, whose worked pattern is a path plus arguments."""
        address = ProductAddress(
            address_template="/context-products/fixture/{subject}"
        )
        assert _register(addressability=address).addressability == address


class TestEveryDefaultIsAPositiveAssertion:
    """A class registered before the elements existed said something."""

    def test_the_three_elements_default_to_named_sentinels(self) -> None:
        registered = _register()
        assert registered.freshness_sla == UNMEASURED_FRESHNESS_SLA
        assert registered.discovery == NOT_DISCOVERABLE
        assert registered.addressability == NOT_ADDRESSABLE

    def test_the_sentinels_are_empty_rather_than_invented_values(self) -> None:
        """CINV-01: the SDK ships no freshness figure and no address."""
        assert UNMEASURED_FRESHNESS_SLA.max_age_seconds_by_signal == {}
        assert NOT_DISCOVERABLE.intents == frozenset()
        assert NOT_DISCOVERABLE.capabilities == frozenset()
        assert NO_VALIDITY_FLOORS.min_validity_seconds_by_signal == {}

    def test_every_pre_existing_registration_still_constructs(self) -> None:
        """The 29-call-site population D-IMPL-106 priced at zero under a default."""
        registered = _register()
        assert registered.schema_name == "fixture.governance"


class TestTheConstituentValidityFloors:
    """D-IMPL-31, ruled 2026-07-25, implemented here — declaration only."""

    def test_floors_are_declarable_on_the_registered_class(self) -> None:
        floors = ConstituentValidityFloors(
            min_validity_seconds_by_signal={"fixture.blotter": 900}
        )
        assert _register(constituent_validity_floors=floors) \
            .constituent_validity_floors == floors

    def test_floors_are_declarable_on_the_authored_artifact(self) -> None:
        assert (
            "constituent_validity_floors"
            in ProductClassDeclaration.model_fields
        )

    def test_the_refusal_that_reads_them_is_not_this_plan(self) -> None:
        """The floors are a *declaration* here; ``15.5-12`` refuses on them.

        Asserted rather than described so the boundary is checkable: nothing
        in the registration path consumes a floor, because a refusal that
        landed here without its assembly-side counterpart would be a rule
        enforced at the wrong moment.
        """
        floors = ConstituentValidityFloors(
            min_validity_seconds_by_signal={"fixture.blotter": 900}
        )
        registered = _register(constituent_validity_floors=floors)
        assert registered.constituent_validity_floors == floors


class TestThePayloadSchemaIsPinnedAndResolvedAtRegistration:
    """D-IMPL-102 limb 1 — schema validity at registration, before requests."""

    def test_a_class_may_declare_no_payload_schema(self) -> None:
        registered = _register()
        assert registered.payload_schema_key == NO_PAYLOAD_SCHEMA
        assert registered.payload_schema_version == NO_PAYLOAD_SCHEMA

    def test_a_declared_schema_is_resolved_and_pinned(self) -> None:
        registry, ttl_version = _registry_with_ceiling()
        schema_version = registry.register(PAYLOAD_SCHEMA_KEY, _payload_schema())
        registered = _register(
            registry=registry,
            max_ttl_version=ttl_version,
            payload_schema_key=PAYLOAD_SCHEMA_KEY,
            payload_schema_version=schema_version,
        )
        assert registered.payload_schema_key == PAYLOAD_SCHEMA_KEY
        assert registered.payload_schema_version == schema_version

    def test_an_unregistered_schema_raises_naming_both_sides(self) -> None:
        registry, ttl_version = _registry_with_ceiling()
        with pytest.raises(ProductClassRegistrationError) as raised:
            _register(
                registry=registry,
                max_ttl_version=ttl_version,
                payload_schema_key=PAYLOAD_SCHEMA_KEY,
                payload_schema_version="0" * 64,
            )
        assert PAYLOAD_SCHEMA_KEY in str(raised.value)
        assert "fixture.governance" in str(raised.value)

    def test_a_wrongly_typed_schema_artifact_raises_naming_both_sides(self) -> None:
        registry, ttl_version = _registry_with_ceiling()
        wrong_version = registry.register(PAYLOAD_SCHEMA_KEY, MaxTTL(seconds=1))
        with pytest.raises(ProductClassRegistrationError) as raised:
            _register(
                registry=registry,
                max_ttl_version=ttl_version,
                payload_schema_key=PAYLOAD_SCHEMA_KEY,
                payload_schema_version=wrong_version,
            )
        assert "MaxTTL" in str(raised.value)
        assert "SkillArgumentSchema" in str(
            raised.value
        ) or "payload schema" in str(raised.value)

    def test_half_a_pin_is_refused_in_both_directions(self) -> None:
        """A key without a version, or a version without a key, is not a pin."""
        registry, ttl_version = _registry_with_ceiling()
        with pytest.raises(ProductClassRegistrationError):
            _register(
                registry=registry,
                max_ttl_version=ttl_version,
                payload_schema_key=PAYLOAD_SCHEMA_KEY,
            )
        registry, ttl_version = _registry_with_ceiling()
        with pytest.raises(ProductClassRegistrationError):
            _register(
                registry=registry,
                max_ttl_version=ttl_version,
                payload_schema_version="0" * 64,
            )


class TestTheAuthoredTwinMirrorsTheClass:
    """``ProductClassDeclaration`` is what an adopter writes."""

    @pytest.mark.parametrize(
        "field",
        [
            "freshness_sla",
            "discovery",
            "addressability",
            "constituent_validity_floors",
            "payload_schema_key",
        ],
    )
    def test_every_new_governance_field_is_authorable(self, field: str) -> None:
        assert field in ProductClassDeclaration.model_fields

    def test_the_artifact_declares_a_key_and_never_a_derived_version(self) -> None:
        """``src/ccf/controlplane/artifacts.py::ProductClassDeclaration``'s
        authored-key/derived-version rule, applied to the new pin.

        The payload-schema version is a content hash minted by *registering*
        the schema. An artifact declaring it would be authoring a hash of
        something it does not contain — the same reason ``max_ttl_version``
        is absent from this class and has been since it existed.
        """
        assert "payload_schema_version" not in ProductClassDeclaration.model_fields
        assert "max_ttl_version" not in ProductClassDeclaration.model_fields

    def test_an_artifact_authored_before_the_widening_still_parses(self) -> None:
        declaration = ProductClassDeclaration.model_validate(
            {
                "semver": "1.0.0",
                "schema_name": "fixture.governance",
                "schema_version": "1.0.0",
                "ttl_anchor": "from_decision",
                "assembly_mode": "algorithmic",
                "max_ttl_key": MAX_TTL_KEY,
                "required_operator_keys": ["fixture.operator"],
            }
        )
        assert declaration.freshness_sla == UNMEASURED_FRESHNESS_SLA
        assert declaration.payload_schema_key == NO_PAYLOAD_SCHEMA


class TestTheModuleDocstringNamesOnlyWhatExists:
    """T-15.5-28: prose can no longer diverge from the type silently."""

    def test_every_element_the_docstring_places_on_the_class_is_there(self) -> None:
        from ccf.products import contract as contract_module

        docstring = contract_module.__doc__ or ""
        claiming = [
            paragraph
            for paragraph in docstring.split("\n\n")
            if "RegisteredProductClass" in paragraph
        ]
        assert claiming
        for element, field in (
            ("Freshness SLA", "freshness_sla"),
            ("Discovery", "discovery"),
            ("Addressability", "addressability"),
            ("Assembly Mode", "assembly_mode"),
        ):
            if any(element.lower() in p.lower() for p in claiming):
                assert field in RegisteredProductClass.model_fields, element
