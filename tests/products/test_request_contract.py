"""The typed request contract — a product asked a question, not configured.

``examples/s1-01`` pins its subject, its temporal boundary and its ``now`` as
literals in artifacts: one company, one frozen instant, one answer. Chapter 1
names that as the thing CCF replaces — *"the difference between the verb
aggregate and the verb assemble."* The root cause was structural rather than
editorial: :class:`~ccf.products.contract.ContextProductContract` had no
surface for the question that provoked it, so the subject and the instant had
nowhere to live but a YAML file.

``D-IMPL-98`` (Dave, 2026-08-11, option (a)) rules the fix: every product class
declares a **typed request contract as a Control Plane artifact**, in the
:class:`~ccf.skills.catalog.SkillArgumentSchema` shape, and subject and instant
become *arguments the caller supplies*. This module holds that surface's
behaviour.

**Two absences are asserted here rather than described, because each is a
security property.**

* **No role field.** A role the caller could put in the request body would
  reintroduce exactly the unverified claim plan ``15.5-06`` closed: the door
  resolves the role from the verified
  :class:`~ccf.products.entitlement.ProductEntitlementGrant` before it
  constructs a :class:`~ccf.projection.plan.Perspective`. Enforced by field
  enumeration in the ``tests/peering/test_trust_policy.py:213`` shape, because
  a docstring cannot fail when a later contributor adds one.
* **No clock.** The caller supplies the instant at serve time and replay feeds
  the *recorded* boundary through the same code path — which is the whole
  reason :meth:`~ccf.projection.engine.ProjectionEngine.execute` reads no clock
  either. A validator that reached for the wall clock would make a request's
  verdict unreproducible, so the module is scanned for one.

Requirements CPS-07, CPS-12.
"""

from __future__ import annotations

import ast
import pathlib
from datetime import datetime, timezone
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import NO_PAYLOAD_SCHEMA, ProductClassRegistrationError
from ccf.products.request import (
    NO_REQUEST_CONTRACT,
    PRODUCT_REQUEST_CONTRACT,
    ProductRequest,
    ProductRequestContract,
    ProductRequestViolation,
    refuse_request,
    refuse_request_contract_pin,
    request_seeds,
)
from ccf.skills.catalog import (
    SkillArgumentElement,
    SkillArgumentMember,
    SkillArgumentProperty,
    SkillArgumentSchema,
)

#: Every field name fragment that would let a caller assert *who they are* in
#: the request body. The door resolves identity from a verified grant; a
#: request that could carry it would be a claim, not a question.
FORBIDDEN_FIELD_MARKERS = (
    "role",
    "principal",
    "actor",
    "tenant",
    "grant",
    "entitle",
    "permission",
    "scope",
)

#: What a wall-clock read looks like in source. The module under test must
#: contain none: the instant is the caller's argument, never the validator's
#: observation.
CLOCK_CALLS = ("now", "utcnow", "today", "time", "monotonic")

CLASS_NAME = "fixture.request"
CLASS_VERSION = "1.0.0"
CONTRACT_KEY = "fixture.request-contract"
INSTANT = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


def _arguments() -> SkillArgumentSchema:
    """A declared parameter surface with a required leaf, an object and a list.

    Three shapes rather than one, so the delegation to
    :func:`~ccf.products.payload.refuse_payload` is exercised at every level
    D-IMPL-103's widening admits rather than only at the root.
    """
    return SkillArgumentSchema(
        properties={
            "required_leaf": SkillArgumentProperty(
                type="string", description="a required top-level parameter"
            ),
            "optional_leaf": SkillArgumentProperty(
                type="integer", description="an optional top-level parameter"
            ),
            "nested": SkillArgumentProperty(
                type="object",
                description="a one-level nested parameter",
                properties={
                    "member": SkillArgumentMember(
                        type="string", description="a nested member"
                    )
                },
                required=("member",),
            ),
            "listed": SkillArgumentProperty(
                type="array",
                description="a list of objects",
                items=SkillArgumentElement(
                    type="object",
                    description="one element",
                    properties={
                        "element_member": SkillArgumentMember(
                            type="string", description="an element member"
                        )
                    },
                    required=("element_member",),
                ),
            ),
        },
        required=("required_leaf",),
    )


def _contract(**overrides: Any) -> ProductRequestContract:
    fields: dict[str, Any] = {
        "semver": "1.0.0",
        "schema_name": CLASS_NAME,
        "schema_version": CLASS_VERSION,
        "arguments": _arguments(),
    }
    fields.update(overrides)
    return ProductRequestContract(**fields)


def _request(**overrides: Any) -> ProductRequest:
    fields: dict[str, Any] = {
        "schema_name": CLASS_NAME,
        "schema_version": CLASS_VERSION,
        "subject": "fixture:subject/one",
        "intent": "fixture-intent",
        "freshness": "fixture-freshness",
        "asked_at": INSTANT,
        "parameters": {"required_leaf": "value"},
    }
    fields.update(overrides)
    return ProductRequest(**fields)


# --- (a) the four address axes, and what is deliberately absent ---------------


def test_the_request_carries_the_four_axes_the_address_pattern_encodes() -> None:
    """§6.3 Addressability at ``docs/CCF_Whitepaper_1-2.md:1465``.

    The worked pattern
    ``/context-products/credit-risk/counterparty/{counterparty-id}?intent=…&freshness=…``
    *"encodes exactly what the agent needs: which entity, for what decision,
    under what temporal requirement."* Four axes, and the instant is the fourth
    because a decision-time assembly is asked *as of* something.
    """
    names = set(ProductRequest.model_fields)
    assert {"subject", "intent", "freshness", "asked_at"} <= names


@pytest.mark.parametrize(
    "field", ["subject", "intent", "freshness", "asked_at", "parameters"]
)
def test_no_address_axis_has_a_default(field: str) -> None:
    """A defaulted axis is a question nobody asked, answered anyway."""
    assert ProductRequest.model_fields[field].is_required(), field


def test_no_field_on_the_request_could_assert_who_is_asking() -> None:
    """T-15.5-32 made structural, in the ``test_trust_policy.py:213`` shape.

    Role is resolved at the door from the verified grant (plan ``15.5-06``).
    A role in the request body is an unverified claim, and a docstring saying
    so cannot fail when someone adds ``requested_role``.
    """
    offending = [
        name
        for name in ProductRequest.model_fields
        if any(marker in name.lower() for marker in FORBIDDEN_FIELD_MARKERS)
    ]
    assert offending == []


def test_the_request_module_reads_no_clock() -> None:
    """T-15.5-34: the instant is supplied, never observed.

    The engine reads no clock deliberately, so that replay feeds the *original*
    boundary through the same code path and gets the same answer. A validator
    that read one would break that for the request surface instead.
    """
    source = pathlib.Path("src/ccf/products/request.py").read_text()
    tree = ast.parse(source)
    reads = [
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in CLOCK_CALLS
    ]
    assert reads == [], reads


# --- (b) the comparison ------------------------------------------------------


def test_a_conforming_request_is_accepted() -> None:
    assert refuse_request(request=_request(), declared=_contract()) is None


def test_a_conforming_request_may_fill_every_declared_level() -> None:
    request = _request(
        parameters={
            "required_leaf": "value",
            "optional_leaf": 3,
            "nested": {"member": "value"},
            "listed": [{"element_member": "value"}],
        }
    )
    assert refuse_request(request=request, declared=_contract()) is None


def test_an_undeclared_parameter_is_refused_naming_both_sides() -> None:
    request = _request(parameters={"required_leaf": "value", "smuggled": "x"})
    violation = refuse_request(request=request, declared=_contract())
    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "undeclared-parameter"
    assert violation.key == "smuggled"
    assert "smuggled" in violation.presented_keys
    assert "smuggled" not in violation.declared_keys
    assert violation.declared_keys == frozenset(_arguments().properties)


def test_a_missing_required_parameter_is_refused_naming_it() -> None:
    violation = refuse_request(request=_request(parameters={}), declared=_contract())
    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "missing-required-parameter"
    assert violation.key == "required_leaf"
    assert violation.declared_type == "string"


def test_a_mistyped_parameter_is_refused_naming_both_types() -> None:
    request = _request(parameters={"required_leaf": 1})
    violation = refuse_request(request=request, declared=_contract())
    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "type-mismatch"
    assert violation.declared_type == "string"
    assert violation.presented_type == "int"


def test_a_violation_one_level_down_keeps_its_dotted_path() -> None:
    """D-IMPL-103's widening made "which parameter" ambiguous; the path answers."""
    request = _request(
        parameters={"required_leaf": "value", "nested": {"member": 1}}
    )
    violation = refuse_request(request=request, declared=_contract())
    assert isinstance(violation, ProductRequestViolation)
    assert violation.key == "nested.member"


def test_a_violation_inside_a_declared_list_keeps_its_element_path() -> None:
    request = _request(
        parameters={
            "required_leaf": "value",
            "listed": [{"element_member": "value"}, {"element_member": 1}],
        }
    )
    violation = refuse_request(request=request, declared=_contract())
    assert isinstance(violation, ProductRequestViolation)
    assert violation.key == "listed[].element_member"


def test_a_request_addressed_to_another_class_is_refused() -> None:
    """A contract is the request surface *of one class*, at one lane."""
    violation = refuse_request(
        request=_request(schema_name="fixture.other"), declared=_contract()
    )
    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "class-mismatch"
    assert violation.key == "schema_name"
    assert violation.declared_type == CLASS_NAME
    assert violation.presented_type == "fixture.other"


def test_a_request_addressed_to_another_lane_is_refused() -> None:
    violation = refuse_request(
        request=_request(schema_version="2.0.0"), declared=_contract()
    )
    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "class-mismatch"
    assert violation.key == "schema_version"


def test_the_comparison_is_pure_over_its_arguments() -> None:
    """Same pair, same verdict — twice, with nothing registered anywhere."""
    request = _request(parameters={"required_leaf": "value", "smuggled": "x"})
    first = refuse_request(request=request, declared=_contract())
    second = refuse_request(request=request, declared=_contract())
    assert first == second


# --- (c) addressability: the question asked is a value -----------------------


def test_two_requests_differing_only_in_subject_hash_differently() -> None:
    """§6.3 Addressability: *which* entity is part of the question asked.

    If the subject did not reach the content address, two different questions
    would pin identically and plan ``15.5-13``'s query pin could not tell them
    apart in the replay record (T-15.5-33).
    """
    one = content_hash(_request(subject="fixture:subject/one"))
    two = content_hash(_request(subject="fixture:subject/two"))
    assert one != two


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("intent", "fixture-other-intent"),
        ("freshness", "fixture-other-freshness"),
        ("asked_at", datetime(2026, 8, 11, 13, 0, tzinfo=timezone.utc)),
    ],
)
def test_every_other_axis_also_reaches_the_content_address(
    field: str, value: object
) -> None:
    assert content_hash(_request()) != content_hash(_request(**{field: value}))


def test_the_same_question_asked_twice_pins_identically() -> None:
    assert content_hash(_request()) == content_hash(_request())


# --- (c2) the anchor starts the walk, D-IMPL-111 limb (a) --------------------


def test_the_seeds_a_request_implies_are_its_subject_and_nothing_else() -> None:
    """D-IMPL-111 limb (a): the entity anchor is where the walk begins.

    One element, and it is the subject — not the intent, not a parameter, not
    a derived neighbourhood. Anything else would be the SDK inventing a walk
    on the deployment's behalf out of values it does not interpret.
    """
    assert request_seeds(_request(subject="fixture:subject/one")) == frozenset(
        {"fixture:subject/one"}
    )


def test_two_subjects_imply_two_different_walks() -> None:
    """The one derivation both the serve path and replay run through.

    If this ever returned the same set for two subjects, two questions would
    compile to the same graph query again and ``DI-15.5-07`` would be back
    with a test asserting it was fixed.
    """
    assert request_seeds(_request(subject="fixture:subject/one")) != request_seeds(
        _request(subject="fixture:subject/two")
    )


def test_no_request_implies_no_seeds() -> None:
    """The pre-D-IMPL-111 posture, which every older record replays under.

    ``None`` rather than the empty frozenset, and the difference is load
    bearing at the seam: the empty set is a legal ``GraphQuery.seeds`` value
    meaning *these zero entities start the walk*, while ``None`` means *the
    plan's own seed classes and nothing else*.
    """
    assert request_seeds(None) is None


# --- (d) the artifact class and its placement --------------------------------


def test_the_contract_is_a_control_plane_artifact_class() -> None:
    assert PRODUCT_REQUEST_CONTRACT.class_id == "ccf.product-request-contract"
    assert PRODUCT_REQUEST_CONTRACT.contract is ProductRequestContract


def test_the_contract_declares_its_own_semver_lane() -> None:
    with pytest.raises(ValueError):
        _contract(semver="not-a-semver")


def test_the_contract_reuses_the_already_proven_schema_machinery() -> None:
    """D-IMPL-103: reuse, never a second machinery.

    Asserted by type identity rather than claimed in a comment — the ruling's
    whole content is that the shape a skill declares its arguments in is the
    shape a product declares its request in.
    """
    annotation = ProductRequestContract.model_fields["arguments"].annotation
    assert annotation is SkillArgumentSchema


def test_the_request_contract_does_not_widen_the_http_schema_served_set() -> None:
    """The 15.5-03 placement, applied again and asserted rather than assumed.

    ``SDK_ARTIFACT_CLASSES`` *is* the set the HTTP ``GET /schema`` route and
    ``ccf schema export`` enumerate. This class joins neither SDK mapping — it
    is adopter-registered against its real contract, exactly as
    ``ccf.peering-trust-policy`` and ``ccf.product-entitlement-policy`` are —
    so it gets a committed schema through the third bucket
    ``tools/dump_schemas.py`` discovers and the served set is byte-unchanged.
    """
    from ccf.deployment.classes import (
        SDK_ARTIFACT_CLASSES,
        SDK_VERSIONED_ARTIFACT_CLASSES,
    )

    assert PRODUCT_REQUEST_CONTRACT.class_id not in SDK_ARTIFACT_CLASSES
    assert PRODUCT_REQUEST_CONTRACT.class_id not in SDK_VERSIONED_ARTIFACT_CLASSES


def test_the_class_declaration_authors_the_key_and_not_the_version() -> None:
    """Authored key, derived version — ``artifacts.py:502-510``, third instance.

    The version pinning a request contract is minted by *registering* it and is
    a content hash of what was registered. An artifact declaring it would be
    authoring a hash of something it does not contain.
    """
    assert "request_contract_key" in ProductClassDeclaration.model_fields
    assert "request_contract_version" not in ProductClassDeclaration.model_fields


def test_a_declaration_written_before_this_plan_still_parses() -> None:
    declaration = ProductClassDeclaration(
        semver="1.0.0",
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key="fixture.max-ttl",
        required_operator_keys=("fixture.operator",),
    )
    assert declaration.request_contract_key == NO_REQUEST_CONTRACT
    assert declaration.payload_schema_key == NO_PAYLOAD_SCHEMA


# --- (e) refused at registration, in the MAX_TTL voice -----------------------


def _registry_with_contract() -> tuple[ControlPlaneRegistry, str]:
    registry = ControlPlaneRegistry()
    version = registry.register(CONTRACT_KEY, _contract())
    return registry, version


def _pin(**overrides: Any) -> None:
    registry, version = overrides.pop("pair", _registry_with_contract())
    fields: dict[str, Any] = {
        "registry": registry,
        "schema_name": CLASS_NAME,
        "schema_version": CLASS_VERSION,
        "request_contract_key": CONTRACT_KEY,
        "request_contract_version": version,
    }
    fields.update(overrides)
    refuse_request_contract_pin(**fields)


def test_an_undeclared_pin_is_accepted() -> None:
    """A class that declares no request contract is a legitimate state."""
    _pin(
        request_contract_key=NO_REQUEST_CONTRACT,
        request_contract_version=NO_REQUEST_CONTRACT,
    )


def test_half_a_pin_is_refused() -> None:
    with pytest.raises(ProductClassRegistrationError, match="half a request-contract"):
        _pin(request_contract_version=NO_REQUEST_CONTRACT)


def test_a_pin_naming_nothing_registered_is_refused() -> None:
    with pytest.raises(ProductClassRegistrationError, match="not registered"):
        _pin(request_contract_key="fixture.absent")


def test_a_pin_naming_something_that_is_not_a_request_contract_is_refused() -> None:
    registry = ControlPlaneRegistry()
    version = registry.register(CONTRACT_KEY, _arguments())
    with pytest.raises(ProductClassRegistrationError, match="not a request contract"):
        _pin(pair=(registry, version))


def test_a_contract_declared_for_another_class_is_refused() -> None:
    """The cross-check a payload schema cannot make, because it names no class."""
    registry = ControlPlaneRegistry()
    version = registry.register(
        CONTRACT_KEY, _contract(schema_name="fixture.other")
    )
    with pytest.raises(ProductClassRegistrationError, match="fixture.other"):
        _pin(pair=(registry, version))


def test_a_contract_declared_for_another_lane_is_refused() -> None:
    registry = ControlPlaneRegistry()
    version = registry.register(CONTRACT_KEY, _contract(schema_version="2.0.0"))
    with pytest.raises(ProductClassRegistrationError, match="2.0.0"):
        _pin(pair=(registry, version))


# --- (f) reachable FROM registration, not merely defined --------------------
#
# Plan 15.5-08 shipped `refuse_request_contract_pin` complete and tested but
# could not wire it: `register_product_class` and `RegisteredProductClass` both
# live in `src/ccf/products/contract.py`, which concurrent plan 15.5-11 owned
# that wave. The section above proves the refusal is CORRECT; this one proves
# it is REACHED — which is the difference between a check and a check that
# runs, and the whole of what 15.5-15 inherited (D-IMPL-108).


def _register(**overrides: Any) -> Any:
    """Register a class through the real factory, with a valid MAX_TTL."""
    from ccf.products.contract import MaxTTL, register_product_class

    registry, version = overrides.pop("pair", _registry_with_contract())
    max_ttl_version = registry.register("fixture.max-ttl", MaxTTL(seconds=600))
    fields: dict[str, Any] = {
        "registry": registry,
        "schema_name": CLASS_NAME,
        "schema_version": CLASS_VERSION,
        "ttl_anchor": "from_decision",
        "assembly_mode": "algorithmic",
        "max_ttl_key": "fixture.max-ttl",
        "max_ttl_version": max_ttl_version,
        "request_contract_key": CONTRACT_KEY,
        "request_contract_version": version,
    }
    fields.update(overrides)
    return register_product_class(**fields)


def test_registration_refuses_a_half_declared_request_contract_pin() -> None:
    """The wiring 15.5-08 could not take, taken.

    What would fail here: `register_product_class` calling the payload pin
    refusal and not this one — which is exactly the state the tree was in
    between plan 15.5-08 and plan 15.5-15, with the refusal defined, tested,
    and reached by nobody.
    """
    with pytest.raises(
        ProductClassRegistrationError, match="half a request-contract"
    ):
        _register(request_contract_version=NO_REQUEST_CONTRACT)


def test_registration_refuses_a_contract_pinned_onto_another_class() -> None:
    """The cross-check no payload schema can make, now made at wiring time."""
    registry = ControlPlaneRegistry()
    version = registry.register(
        CONTRACT_KEY, _contract(schema_name="fixture.other")
    )
    with pytest.raises(ProductClassRegistrationError, match="fixture.other"):
        _register(pair=(registry, version))


def test_registration_carries_the_pin_onto_the_registered_class() -> None:
    """The mirror fields exist and are filled from what was resolved.

    Resolved at registration rather than trusted from the declaration, on
    `max_ttl_version`'s own discipline: the surface a question was validated
    against has to be re-resolvable years later for the decision to replay.
    """
    registry, version = _registry_with_contract()
    registered = _register(pair=(registry, version))

    assert registered.request_contract_key == CONTRACT_KEY
    assert registered.request_contract_version == version


def test_a_registration_written_before_this_plan_says_what_it_always_said() -> None:
    """Both mirror fields default to the sentinel, so no call site moves.

    What would fail here: making either field required, which would break
    every `register_product_class` call in this tree and in every adopter's —
    and would do it to say something none of them ever meant to say.
    """
    registered = _register(
        request_contract_key=NO_REQUEST_CONTRACT,
        request_contract_version=NO_REQUEST_CONTRACT,
    )

    assert registered.request_contract_key == NO_REQUEST_CONTRACT
    assert registered.request_contract_version == NO_REQUEST_CONTRACT


def test_the_sentinel_is_one_value_read_from_two_modules() -> None:
    """`ccf.products.request` re-exports it; it is not a second constant.

    What would fail here: the two modules drifting to two spellings of "no
    contract", at which point a class pinned with one would look half-declared
    to the other. Identity, not equality, because two equal strings is exactly
    the state this asserts against.
    """
    from ccf.products import contract as contract_module
    from ccf.products import request as request_module

    assert (
        request_module.NO_REQUEST_CONTRACT
        is contract_module.NO_REQUEST_CONTRACT
    )


def test_no_content_address_moves_because_of_the_pin() -> None:
    """The mirror fields are governance, not payload — asserted, not assumed.

    `RegisteredProductClass` is a `CCFContract`, so adding two fields changes
    ITS canonical bytes. That is only harmless if it is inside no content
    address, which is the thing this asserts rather than the thing it assumes:
    no addressed contract in the tree carries a `RegisteredProductClass`, and
    the vessel `run_gates` admits — the value replay re-derives an address over
    — has exactly the fields it had before this plan.

    What would fail here: a later change hanging the registered class off the
    product, at which point every address recorded before it would differ from
    the one the same product produced after, and D-IMPL-100's ruling for the
    debt field would have been needed for this one too.

    ``debt_evidence`` joined the enumeration under D-IMPL-118 (plan 15.6-06),
    ``source_refresh_recency`` under the same ruling (plan 15.6-07) and
    ``obligation_in_force`` under it again (plan 15.6-08) — the third and last
    of the Track B members the ruling prices identically. That is what this
    assertion is *for*: a field landing inside the delivered bytes is a
    reviewable event with a ruling behind it, never a quiet edit.
    """
    from ccf.contracts.base import CCFContract
    from ccf.products.contract import (
        ContextProductContract,
        RegisteredProductClass,
    )

    assert set(ContextProductContract.model_fields) == {
        "schema_name",
        "schema_version",
        "plan_id",
        "tenant_id",
        "temporal_boundary",
        "expires_at",
        "ttl_anchor",
        "lineage",
        "payload",
        "debt",
        "debt_evidence",
        "source_refresh_recency",
        "obligation_in_force",
    }

    def _reaches(model: type[CCFContract], seen: set[type]) -> bool:
        if model in seen:
            return False
        seen.add(model)
        for field in model.model_fields.values():
            annotation = field.annotation
            if annotation is RegisteredProductClass:
                return True
            if isinstance(annotation, type) and issubclass(
                annotation, CCFContract
            ):
                if _reaches(annotation, seen):
                    return True
        return False

    assert not _reaches(ContextProductContract, set())
