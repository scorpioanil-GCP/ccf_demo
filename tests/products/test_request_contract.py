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
  enumeration in the
  ``tests/peering/test_trust_policy.py::test_no_field_on_the_contract_could_express_a_verification_skip``
  shape, because
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
import importlib.util
import pathlib
import shutil
import sys
from datetime import datetime, timezone
from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import NO_PAYLOAD_SCHEMA, ProductClassRegistrationError
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
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
    """T-15.5-32 made structural, in the shape of
    ``tests/peering/test_trust_policy.py::test_no_field_on_the_contract_could_express_a_verification_skip``.

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
    """Authored key, derived version —
    ``src/ccf/controlplane/artifacts.py::ProductClassDeclaration``, third
    instance.

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
    of the Track B members the ruling prices identically. ``computed_empty``
    joined at ``24.6-05`` under ``D-IMPL-242`` amendment 1 (ledger row
    ``24.6-L-06``): a served empty answer carries the search behind it. It is
    hash-transparent at ``None``, so no address recorded before it moved —
    measured by
    ``tests/contracts/test_hash_transparency.py::test_a_product_with_no_finding_hashes_as_it_did``
    rather than argued here. That is what this assertion is *for*: a field
    landing inside the delivered bytes is a reviewable event with a ruling
    behind it, never a quiet edit.
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
        "computed_empty",
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


# --- `from_declared` — the DeclaredArtifact-to-typed-contract path -----------
#
# `D-IMPL-126` item (1): a request contract is reachable from the
# `DeclaredArtifact` a manifest returns by one named call, rather than by the
# four-field hand-build every adopter would otherwise copy out of
# `examples/s1-01-hello-context-product/deployment.py::read`.

#: The committed artifact the equivalence case reads. Read from disk rather
#: than inlined, so the assertion is against the document an adopter actually
#: ships — an inline copy would drift the moment the file did, and would prove
#: only that the method agrees with the test's own idea of the file.
REQUEST_CONTRACT_ARTIFACT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "examples"
    / "s1-01-hello-context-product"
    / "artifacts"
    / "request-contract.yaml"
)


def _declared(**overrides: Any) -> DeclaredArtifact:
    """A ``DeclaredArtifact`` carrying a well-formed request-contract body."""
    fields: dict[str, Any] = {
        "semver": "1.0.0",
        "class_id": CONTRACT_KEY,
        "declaration": {
            "schema_name": CLASS_NAME,
            "schema_version": CLASS_VERSION,
            "arguments": _arguments().model_dump(mode="json"),
        },
    }
    fields.update(overrides)
    return DeclaredArtifact(**fields)


def test_from_declared_reads_the_document_lane_and_the_three_keys() -> None:
    """The four fields come from the four places they actually live.

    ``semver`` is the *document's* lane and the two ``schema_*`` keys are the
    *class's* — two lanes, two things versioned (D-IMPL-98) — so a method that
    read the class lane out of ``semver`` would pass a shape check and be wrong.
    """
    contract = ProductRequestContract.from_declared(_declared(semver="2.3.4"))

    assert contract.semver == "2.3.4"
    assert contract.schema_name == CLASS_NAME
    assert contract.schema_version == CLASS_VERSION
    assert contract.arguments == _arguments()


def test_from_declared_equals_the_hand_build_for_the_committed_artifact() -> None:
    """The equivalence that makes this a replacement, not a second way.

    ``examples/s1-01-hello-context-product/deployment.py::read`` hand-builds
    a :class:`ProductRequestContract` field by field from the committed
    ``request-contract.yaml``. This asserts ``from_declared`` produces a model
    **equal** to that build from the same document on disk — so plan ``16-05``
    (or HW-1) can switch the example over knowing nothing moves.

    Asserted on the model and on its content address, never on a ``repr``: a
    repr comparison would pass for two models whose canonical bytes differ.
    """
    document = yaml.safe_load(
        REQUEST_CONTRACT_ARTIFACT.read_text(encoding="utf-8")
    )
    artifact = DeclaredArtifact(
        semver=document["semver"],
        class_id=document["class_id"],
        declaration=document["declaration"],
    )

    # The hand-build, transcribed from deployment.py::read rather than
    # imported: importing it would make this test agree with the example by
    # construction, which is the one thing it must not do.
    declaration = artifact.declaration
    hand_built = ProductRequestContract(
        semver=artifact.semver,
        schema_name=declaration["schema_name"],
        schema_version=declaration["schema_version"],
        arguments=SkillArgumentSchema.model_validate(declaration["arguments"]),
    )

    assert ProductRequestContract.from_declared(artifact) == hand_built
    assert content_hash(
        ProductRequestContract.from_declared(artifact)
    ) == content_hash(hand_built)


def test_from_declared_names_every_missing_key_in_one_message() -> None:
    """Three missing keys, one refusal — not three exceptions in sequence.

    An adopter fixing a declaration one ``KeyError`` at a time is the papercut
    `D-IMPL-126` item (1) exists to close, so the exhaustive message is the
    behaviour and not a nicety.
    """
    with pytest.raises(ValueError) as raised:
        ProductRequestContract.from_declared(_declared(declaration={}))

    message = str(raised.value)
    for key in ("schema_name", "schema_version", "arguments"):
        assert key in message


@pytest.mark.parametrize(
    "absent", ["schema_name", "schema_version", "arguments"]
)
def test_from_declared_refuses_each_key_singly_by_name(absent: str) -> None:
    """Each key is refused on its own, and the message names *that* key."""
    declaration = dict(_declared().declaration)
    declaration.pop(absent)

    with pytest.raises(ValueError) as raised:
        ProductRequestContract.from_declared(
            _declared(declaration=declaration)
        )

    assert absent in str(raised.value)


def test_from_declared_names_both_rejected_shapes_in_its_own_docstring() -> None:
    """The rationale is on the **method**, where a later reader will look.

    Deliberately not the module docstring: ``tools/dump_schemas.py`` copies
    module and class docstrings verbatim into schema ``description`` fields, so
    a method docstring owes no schema regeneration. And a rejection recorded
    nowhere is a rejection that gets re-proposed.
    """
    doc = ProductRequestContract.from_declared.__doc__
    assert doc is not None
    assert "D-IMPL-84" in doc
    assert "request-contract" in doc
    assert "SDK_VERSIONED_ARTIFACT_CLASSES" in doc


def test_the_manifest_loader_shape_was_not_taken() -> None:
    """``resolve_artifact_class`` stays a total three-branch function.

    A ``*.request-contract`` suffix branch would have the SDK claim a name
    across every adopter namespace, where `D-IMPL-84` draws the line at exactly
    one prefix. Asserted against the source because the rejection is only worth
    recording if a later contributor adding the branch fails.
    """
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "ccf"
        / "deployment"
        / "classes.py"
    ).read_text(encoding="utf-8")
    assert "request-contract" not in source


def test_the_equivalence_case_reads_the_committed_artifact_from_disk() -> None:
    """The path literal is in this module, and the file it names exists."""
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    assert "s1-01-hello-context-product" in source
    assert "request-contract.yaml" in source
    assert REQUEST_CONTRACT_ARTIFACT.is_file()


# --- (g) declared and always refused — 24.5-L-12, 24.5-L-13 -------------------
#
# The Standard's declared-but-inert parameter (§2.4) and its `400
# not_supported_at_tier` (§9). The parameter set lives in the ARTIFACT and the
# verdict comes from the declaration; no spine constant carries it. Criterion
# 15's control below plants one in a scratch copy of the module and shows it
# decides nothing — because the No-Hardcoding lint does not fire on a
# parameter-name set (RESEARCH Pitfall 7), this contract test is the gate.

#: Test deployment vocabulary: the inert parameter and its declared reason.
#: The SDK holds neither (CINV-01).
INERT_PARAMETER = "as_of"
INERT_REASON = "fixture tier reason: time travel arrives at a later tier"

#: The real module the scratch-copy control reads. Resolved from this file's
#: own path, never from ``Path.cwd()``.
REQUEST_MODULE = (
    pathlib.Path(__file__).resolve().parents[2] / "src" / "ccf" / "products" / "request.py"
)


def _inert_contract(**overrides: Any) -> ProductRequestContract:
    """The fixture contract, declaring one parameter inert."""
    return _contract(
        unsupported_arguments={INERT_PARAMETER: INERT_REASON}, **overrides
    )


def test_a_declared_and_always_refused_parameter_is_refused_from_the_declaration() -> None:
    """``24.5-L-13``: the tier verdict, and every one of its three ``detail`` tokens.

    What would fail here: the field existing on the contract but
    ``refuse_request`` never reading it — the state the four ladder configs
    were in, with ``unsupported_arguments:`` authored and enforced by each
    example's own code after the SDK had already said the request conformed.
    """
    request = _request(
        parameters={"required_leaf": "value", INERT_PARAMETER: "2026-01-01"}
    )
    violation = refuse_request(request=request, declared=_inert_contract())

    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "not-supported-at-tier"
    assert violation.key == INERT_PARAMETER
    assert violation.declared_type is None
    assert violation.presented_type == "str"
    assert violation.declared_keys == frozenset(_arguments().properties)
    assert INERT_PARAMETER in violation.presented_keys
    # The Standard's status token, the parameter name and the declared prose:
    # all three, so a reader of the sentence sees what the declaration said.
    assert "400" in violation.detail
    assert "not_supported_at_tier" in violation.detail
    assert INERT_PARAMETER in violation.detail
    assert INERT_REASON in violation.detail


def test_the_tier_verdict_precedes_the_payload_comparison() -> None:
    """Address → tier → payload, and the order is what makes the reason readable.

    An inert parameter is typically not in ``arguments.properties``, so the
    payload comparison run first would call it ``undeclared-parameter`` and
    hide the declared reason. Presenting the inert parameter AND a mistyped
    declared one settles which step spoke: the tier step.
    """
    request = _request(
        parameters={"required_leaf": 1, INERT_PARAMETER: "2026-01-01"}
    )
    violation = refuse_request(request=request, declared=_inert_contract())

    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "not-supported-at-tier"
    assert violation.key == INERT_PARAMETER


def test_the_address_check_still_precedes_the_tier_step() -> None:
    """A request to another class never reaches the tier step (T-24.5-16)."""
    request = _request(
        schema_name="fixture.other",
        parameters={"required_leaf": "value", INERT_PARAMETER: "2026-01-01"},
    )
    violation = refuse_request(request=request, declared=_inert_contract())

    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "class-mismatch"


def test_an_absent_inert_parameter_is_not_refused() -> None:
    """Declaring a parameter inert refuses its *presence*, never its absence."""
    assert refuse_request(request=_request(), declared=_inert_contract()) is None


def test_an_inert_parameter_is_refused_whatever_its_type() -> None:
    """The declaration refuses the parameter, not a type of it."""
    for presented in (1, 1.5, True, None, {"nested": "x"}, ["listed"]):
        request = _request(
            parameters={"required_leaf": "value", INERT_PARAMETER: presented}
        )
        violation = refuse_request(request=request, declared=_inert_contract())
        assert isinstance(violation, ProductRequestViolation), presented
        assert violation.reason == "not-supported-at-tier", presented
        assert violation.presented_type == type(presented).__name__


def test_a_declaration_without_unsupported_arguments_still_parses() -> None:
    """The pre-phase shape: no key, the empty mapping, nothing refused by tier."""
    contract = ProductRequestContract.from_declared(_declared())

    assert dict(contract.unsupported_arguments) == {}
    assert refuse_request(request=_request(), declared=contract) is None


def test_from_declared_reads_the_optional_fourth_key() -> None:
    """The four ladder configs already author this key; the SDK now reads it."""
    declaration = dict(_declared().declaration)
    declaration["unsupported_arguments"] = {INERT_PARAMETER: INERT_REASON}
    contract = ProductRequestContract.from_declared(
        _declared(declaration=declaration)
    )

    assert dict(contract.unsupported_arguments) == {INERT_PARAMETER: INERT_REASON}


@pytest.mark.parametrize(
    "malformed", [[INERT_PARAMETER], "as_of", {INERT_PARAMETER: 3}, {4: "x"}]
)
def test_from_declared_refuses_a_malformed_unsupported_arguments(
    malformed: Any,
) -> None:
    """Not a mapping of name to prose → refused by name, in the one-error voice."""
    declaration = dict(_declared().declaration)
    declaration["unsupported_arguments"] = malformed

    with pytest.raises(ValueError) as raised:
        ProductRequestContract.from_declared(_declared(declaration=declaration))

    assert "unsupported_arguments" in str(raised.value)


def test_the_reason_vocabulary_has_nine_members_tier_proportion_domain_then_membership() -> None:
    """``24.5-L-12``: the fifth member, in the vocabulary's hyphenated spelling;
    ``24.5-WR-02``: the sixth, appended after it; ``D-IMPL-259``: the two
    domain verdicts, appended after that; ``D-IMPL-264`` D-05: the ninth,
    ``not-in-domain``, appended LAST — appended, never inserted, so a reader
    of an older record's reason meets the same roster prefix."""
    import typing

    from ccf.products.request import ProductRequestViolationReason

    members = typing.get_args(ProductRequestViolationReason)
    assert len(members) == 9
    assert members[-5] == "not-supported-at-tier"
    assert members[-4] == "not-a-proportion"
    assert members[-3:-1] == ("below-minimum", "above-maximum")
    assert members[-1] == "not-in-domain"


# --- (g) the tolerance interval: a request number that is not a proportion ---
#
# ``24.5-REVIEW.md`` WR-02, ruled by Dave 2026-09-02: a negative
# ``debt_tolerance`` is refused BY NAME at the request/class boundary, in the
# contract-refusal family, so it can never reach the debt gate as a
# "tightening" and coerce every serve into a ``409`` whose ``declared`` names a number no class
# declared. The interval is the one ``ServeObligations`` holds the CLASS's
# ceiling to (``24.5-L-14``): ``D_c`` is a proportion.


def _tolerance_contract(**overrides: Any) -> ProductRequestContract:
    """The fixture contract, declaring the Standard's universal tolerance as a number."""
    arguments = _arguments()
    properties = dict(arguments.properties)
    properties[DEBT_TOLERANCE_PARAMETER] = SkillArgumentProperty(
        type="number", description="the caller's D_c ceiling; a proportion"
    )
    return _contract(
        arguments=SkillArgumentSchema(
            properties=properties, required=arguments.required
        ),
        **overrides,
    )


def _tolerance_request(value: object) -> ProductRequest:
    return _request(
        parameters={"required_leaf": "value", DEBT_TOLERANCE_PARAMETER: value}
    )


@pytest.mark.parametrize(
    "presented",
    [-1, Decimal("-0.1"), Decimal("1.5"), Decimal("Infinity"), Decimal("NaN")],
    ids=["negative-int", "negative-decimal", "over-one", "infinite", "nan"],
)
def test_a_tolerance_that_is_not_a_proportion_is_refused_by_name(
    presented: object,
) -> None:
    """WR-02: outside ``[0, 1]`` (or not finite) → ``not-a-proportion`` naming the parameter.

    What would fail here: ``refuse_request`` conforming the request on its
    declared TYPE alone, which is the shipped state WR-02 measured — the
    value then reached the gate as a "tightening" and refused every product
    with ``declared="-1"``.
    """
    violation = refuse_request(
        request=_tolerance_request(presented), declared=_tolerance_contract()
    )

    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "not-a-proportion"
    assert violation.key == DEBT_TOLERANCE_PARAMETER
    assert violation.declared_type == "number"
    assert violation.presented_type == type(presented).__name__
    assert violation.declared_keys == frozenset(_tolerance_contract().arguments.properties)
    assert DEBT_TOLERANCE_PARAMETER in violation.presented_keys
    assert DEBT_TOLERANCE_PARAMETER in violation.detail
    assert str(presented) in violation.detail
    assert "[0, 1]" in violation.detail
    assert "24.5-L-14" in violation.detail


@pytest.mark.parametrize(
    "presented",
    [0, 1, Decimal("0"), Decimal("1"), Decimal("0.25")],
    ids=["zero-int", "one-int", "zero-decimal", "one-decimal", "quarter"],
)
def test_a_tolerance_inside_the_unit_interval_conforms(presented: object) -> None:
    """The closed interval, both ends included, as the class-side validator reads it."""
    assert (
        refuse_request(
            request=_tolerance_request(presented), declared=_tolerance_contract()
        )
        is None
    )


def test_the_tolerance_step_is_last_so_earlier_verdicts_keep_their_names() -> None:
    """Order: address → tier → payload → tolerance; a value never reaches the interval check under an earlier verdict.

    Three controls, one per earlier step that could see the same key:
    undeclared → ``undeclared-parameter``; declared inert →
    ``not-supported-at-tier``; declared ``number`` but presented as a string →
    ``type-mismatch``. The interval is only ever judged on a declared,
    honored, well-typed number.
    """
    undeclared = refuse_request(
        request=_tolerance_request(-1), declared=_contract()
    )
    assert isinstance(undeclared, ProductRequestViolation)
    assert undeclared.reason == "undeclared-parameter"

    inert = refuse_request(
        request=_tolerance_request(-1),
        declared=_contract(
            unsupported_arguments={DEBT_TOLERANCE_PARAMETER: "never honored here"}
        ),
    )
    assert isinstance(inert, ProductRequestViolation)
    assert inert.reason == "not-supported-at-tier"

    mistyped = refuse_request(
        request=_tolerance_request("-1"), declared=_tolerance_contract()
    )
    assert isinstance(mistyped, ProductRequestViolation)
    assert mistyped.reason == "type-mismatch"

    # Phase 24.5 close panel (2026-09-03): three reviewers claimed a FLOAT
    # (-0.1, 1.5, nan, inf) slips past the interval step and reaches the gate.
    # Measured and REJECTED: a float is not a ``number`` in this tree
    # (``ccf.products.payload._matches`` — binary floating point cannot reach
    # a content address), so the payload comparison names it first. Pinned
    # here so the rejection stays measured rather than remembered.
    for presented in (-0.1, 1.5, float("nan"), float("inf")):
        as_float = refuse_request(
            request=_tolerance_request(presented), declared=_tolerance_contract()
        )
        assert isinstance(as_float, ProductRequestViolation), presented
        assert as_float.reason == "type-mismatch", presented
        assert as_float.presented_type == "float"


def _string_collection_constants(source: str) -> list[str]:
    """Module-level ``frozenset``/``set``/``tuple`` constants of string literals.

    The shape a spine-held inert-parameter set would take. ``_DECLARATION_KEYS``
    is a tuple of *names*, not of string literals, and ``_REASONS`` is a dict,
    so neither matches — which is the point: this reads the elements, not the
    constructor.
    """
    collections = {"frozenset", "set", "tuple"}
    found: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        elif isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        else:
            continue
        if value is None:
            continue
        elements: list[ast.expr] | None = None
        if isinstance(value, (ast.Set, ast.Tuple)):
            elements = list(value.elts)
        elif (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in collections
            and len(value.args) == 1
            and isinstance(value.args[0], (ast.Set, ast.Tuple, ast.List))
        ):
            elements = list(value.args[0].elts)
        if elements is None or not elements:
            continue
        if all(
            isinstance(element, ast.Constant) and isinstance(element.value, str)
            for element in elements
        ):
            found.extend(ast.unparse(target) for target in targets)
    return found


def _planted_copy(tmp_path: pathlib.Path) -> tuple[ModuleType, pathlib.Path, int]:
    """A scratch copy of the real module with a spine constant planted.

    Returns the imported copy, its path, and the planted line number. The
    copy — never ``src/`` — is what the control reads, on the reasoning
    ``tests/products/test_refusal_envelope.py::sabotaged_root`` gives: an
    edit-and-revert control leaves nothing behind to show it fired.
    """
    copy = tmp_path / "request_with_plant.py"
    shutil.copyfile(REQUEST_MODULE, copy)
    lines = copy.read_text(encoding="utf-8").splitlines(keepends=True)
    # Plant it immediately after the `__ccf_mode__` line, at module level.
    anchor = next(i for i, line in enumerate(lines) if line.startswith("__ccf_mode__"))
    plant = f'INERT_PARAMETERS = frozenset({{"{INERT_PARAMETER}"}})\n'
    lines.insert(anchor + 1, plant)
    copy.write_text("".join(lines), encoding="utf-8")
    planted_line = anchor + 2  # 1-based

    spec = importlib.util.spec_from_file_location("request_with_plant", copy)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: the copy carries `from __future__ import
    # annotations`, and pydantic resolves a model's forward references through
    # `sys.modules[<module name>]`, so an unregistered copy's `ProductRequest`
    # is "not fully defined" the moment it is constructed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, copy, planted_line


def test_a_planted_spine_constant_does_not_decide_the_verdict(
    tmp_path: pathlib.Path,
) -> None:
    """Criterion 15's control: the declaration decides, and code cannot.

    Three limbs. **(a)** A copy of the real module carries
    ``INERT_PARAMETERS = frozenset({"as_of"})`` at module level. Against a
    declaration whose ``unsupported_arguments`` is EMPTY and which declares
    ``as_of`` as an ordinary argument, the copy's ``refuse_request`` returns
    ``None`` for a request presenting ``as_of`` — the planted constant decided
    nothing. Its positive twin — the same request against a declaration that
    names ``as_of`` inert — returns the tier verdict, and that twin is what a
    copy with the tier step removed turns RED (naming
    ``not-supported-at-tier``). **(b)** The No-Hardcoding checker, run
    directly on the copy's source, reports NOTHING for the planted line:
    RECORDED here, not assumed — its three rules are prompt-shape,
    numeric-table and factory-bypass, and a parameter-name set is none of
    them (RESEARCH Pitfall 7), which is exactly why this contract test is the
    gate and the lint is not. **(c)** The REAL module holds no module-level
    ``frozenset``/``set``/``tuple`` constant whose elements are all string
    literals.
    """
    from tools.lints import no_hardcoding

    copy, copy_path, planted_line = _planted_copy(tmp_path)
    assert copy.INERT_PARAMETERS == frozenset({INERT_PARAMETER})

    # (a) — build the world out of the COPY's classes, never the real ones.
    arguments = SkillArgumentSchema(
        properties={
            "required_leaf": SkillArgumentProperty(
                type="string", description="a required top-level parameter"
            ),
            INERT_PARAMETER: SkillArgumentProperty(
                type="string", description="declared as an ordinary argument"
            ),
        },
        required=("required_leaf",),
    )
    empty_declaration = copy.ProductRequestContract(
        semver="1.0.0",
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        arguments=arguments,
    )
    request = copy.ProductRequest(
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        subject="fixture:subject/one",
        intent="fixture-intent",
        freshness="fixture-freshness",
        asked_at=INSTANT,
        parameters={"required_leaf": "value", INERT_PARAMETER: "2026-01-01"},
    )
    assert copy.refuse_request(request=request, declared=empty_declaration) is None

    inert_declaration = copy.ProductRequestContract(
        semver="1.0.0",
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        arguments=arguments,
        unsupported_arguments={INERT_PARAMETER: INERT_REASON},
    )
    twin = copy.refuse_request(request=request, declared=inert_declaration)
    assert twin is not None, (
        "the declaration names the parameter inert and the verdict did not"
        " come from it — the tier step is missing (not-supported-at-tier)"
    )
    assert twin.reason == "not-supported-at-tier"

    # (b) — the lint is silent on the plant; recorded, not assumed.
    findings = no_hardcoding.check_source(
        copy_path.read_text(encoding="utf-8"), copy_path, "request_with_plant"
    )
    on_planted_line = [
        finding for finding in findings if f"{copy_path}:{planted_line} " in finding
    ]
    assert on_planted_line == [], on_planted_line

    # (c) — the real module carries no such constant.
    assert _string_collection_constants(
        REQUEST_MODULE.read_text(encoding="utf-8")
    ) == []


def test_the_string_collection_scan_sees_a_planted_constant(
    tmp_path: pathlib.Path,
) -> None:
    """Limb (c)'s own control: the scan finds the plant in the copy."""
    _, copy_path, _ = _planted_copy(tmp_path)
    assert _string_collection_constants(
        copy_path.read_text(encoding="utf-8")
    ) == ["INERT_PARAMETERS"]


# --- (f) the fifth declaration key: what omission means for this product -----
#
# ``24.6-L-07``; ``D-IMPL-253`` Q2 (Dave: *"Product defaults belong on the
# request contract. They define what omission means for that product."*);
# ``D-IMPL-243`` for the sentinel. **Nothing applies a default at this plan** —
# plan ``24.6-03`` is the resolver step — so what is asserted here is the
# declaration surface and its three refusals.

#: Test deployment vocabulary. The number is the fixture's, never the SDK's
#: (CINV-01): nothing in ``src/ccf/products/request.py`` carries a default.
DEFAULTED_PARAMETER = "optional_leaf"
DEFAULTED_VALUE = 3


def test_a_contract_declaring_a_default_round_trips() -> None:
    contract = _contract(defaults={DEFAULTED_PARAMETER: DEFAULTED_VALUE})
    assert dict(contract.defaults) == {DEFAULTED_PARAMETER: DEFAULTED_VALUE}
    assert (
        ProductRequestContract.model_validate_json(contract.model_dump_json())
        == contract
    )


def test_the_empty_mapping_is_omitted_and_a_declared_default_is_rendered() -> None:
    """``D-IMPL-243``, both halves. The first is the compatibility claim the
    whole field rests on: a contract declaring no default is byte-identical to
    the same contract built before the key existed, so no committed
    request-contract artifact's content address moves."""
    from ccf.contracts.canonical import canonical_bytes

    silent = _contract()
    declaring = _contract(defaults={DEFAULTED_PARAMETER: DEFAULTED_VALUE})

    assert b"defaults" not in canonical_bytes(silent)
    assert canonical_bytes(silent) == canonical_bytes(_contract(defaults={}))
    assert b"defaults" in canonical_bytes(declaring)
    assert canonical_bytes(declaring) != canonical_bytes(silent)


def test_a_declaration_without_defaults_still_parses() -> None:
    """The pre-phase shape: no key, the empty mapping, nothing defaulted."""
    contract = ProductRequestContract.from_declared(_declared())
    assert dict(contract.defaults) == {}


def test_from_declared_reads_the_optional_fifth_key() -> None:
    declaration = dict(_declared().declaration)
    declaration["defaults"] = {DEFAULTED_PARAMETER: DEFAULTED_VALUE}
    contract = ProductRequestContract.from_declared(
        _declared(declaration=declaration)
    )
    assert dict(contract.defaults) == {DEFAULTED_PARAMETER: DEFAULTED_VALUE}


@pytest.mark.parametrize("malformed", [[DEFAULTED_PARAMETER], "optional_leaf", {4: 1}])
def test_from_declared_refuses_a_malformed_defaults(malformed: Any) -> None:
    declaration = dict(_declared().declaration)
    declaration["defaults"] = malformed

    with pytest.raises(ValueError) as raised:
        ProductRequestContract.from_declared(_declared(declaration=declaration))

    assert "defaults" in str(raised.value)


def test_a_default_for_an_undeclared_parameter_is_refused_naming_it() -> None:
    """A default for a parameter the class never declared would widen the
    closed request world by omission — the one thing this artifact exists to
    keep shut."""
    with pytest.raises(ValueError) as raised:
        _contract(defaults={"never_declared": 1})
    assert "never_declared" in str(raised.value)


def test_a_default_for_a_declared_and_always_refused_parameter_is_refused() -> None:
    """A class cannot default a parameter it declares inert: the caller would
    be given, by omission, exactly the value the tier step refuses to accept
    when they supply it (``24.5-L-13``)."""
    with pytest.raises(ValueError) as raised:
        _contract(
            unsupported_arguments={INERT_PARAMETER: INERT_REASON},
            defaults={INERT_PARAMETER: "2026-01-01"},
        )
    assert INERT_PARAMETER in str(raised.value)


def test_a_default_of_the_wrong_type_is_refused_naming_it() -> None:
    """The type check is ``refuse_payload`` over the declared argument, never a
    second reading of "conforms": a default and a caller's value are judged by
    one rule."""
    with pytest.raises(ValueError) as raised:
        _contract(defaults={DEFAULTED_PARAMETER: "not-an-integer"})
    assert DEFAULTED_PARAMETER in str(raised.value)


def test_all_three_offenders_are_named_together_in_one_message() -> None:
    """The exhaustive message is the behavior, not a nicety — the same
    papercut ``from_declared``'s missing-keys message exists to close."""
    with pytest.raises(ValueError) as raised:
        _contract(
            unsupported_arguments={INERT_PARAMETER: INERT_REASON},
            defaults={
                "never_declared": 1,
                INERT_PARAMETER: "2026-01-01",
                DEFAULTED_PARAMETER: "not-an-integer",
            },
        )
    message = str(raised.value)
    assert "never_declared" in message
    assert INERT_PARAMETER in message
    assert DEFAULTED_PARAMETER in message
    assert "24.6-L-07" in message


def test_a_nested_default_is_judged_by_the_same_comparison() -> None:
    """The delegation reaches every level ``D-IMPL-103``'s widening admits: a
    nested object default missing its required member is refused, and the
    well-formed one is admitted (the positive control)."""
    with pytest.raises(ValueError):
        _contract(defaults={"nested": {}})
    assert dict(_contract(defaults={"nested": {"member": "x"}}).defaults) == {
        "nested": {"member": "x"}
    }


def test_the_module_holds_no_default_value_of_its_own() -> None:
    """CINV-01, as a read of the module rather than a claim about it: the SDK
    names the KEY and never a value under it. The key name is the one
    ``defaults``-shaped string the module may carry."""
    source = REQUEST_MODULE.read_text(encoding="utf-8")
    assert '_KEY_DEFAULTS = "defaults"' in source
    assert source.count('_KEY_DEFAULTS = "defaults"') == 1
    assert DEFAULTED_PARAMETER not in source


# ---------------------------------------------------------------------------
# The seventh declaration key — a parameter's valid DOMAIN (`D-IMPL-259`).
# ---------------------------------------------------------------------------
# Dave, 2026-09-05: *"cp-04 `max_depth` has a declared request-contract
# minimum of 1 … Requests below 1 … are governed request-validity refusals
# returned as data; values 1–100 are valid and are never clamped."* And the
# scoping: *"don't turn `1` into a Policy Constraint. It is simply the
# parameter's valid domain."* What is asserted here is the declaration
# surface, its refusals, and the domain step of `refuse_request`. The numbers
# are the fixture's, never the SDK's (CINV-01).

from ccf.products.request import ArgumentDomain  # noqa: E402

DOMAINED_PARAMETER = "optional_leaf"
DOMAIN_FLOOR = 1
DOMAIN_CEILING = 9


def _domained(**overrides: Any) -> ProductRequestContract:
    fields: dict[str, Any] = {
        "argument_domains": {DOMAINED_PARAMETER: ArgumentDomain(minimum=DOMAIN_FLOOR)}
    }
    fields.update(overrides)
    return _contract(**fields)


def test_a_contract_declaring_a_domain_round_trips() -> None:
    contract = _domained()
    assert contract.argument_domains[DOMAINED_PARAMETER].minimum == DOMAIN_FLOOR
    assert contract.argument_domains[DOMAINED_PARAMETER].maximum is None
    assert (
        ProductRequestContract.model_validate_json(contract.model_dump_json())
        == contract
    )


def test_the_empty_domain_mapping_is_omitted_from_the_canonical_bytes() -> None:
    """`D-IMPL-243`'s compatibility claim, for the seventh key: a contract
    declaring no domain is byte-identical to one built before the key existed,
    so no committed request contract's content address moves."""
    from ccf.contracts.canonical import canonical_bytes

    silent = _contract()
    assert b"argument_domains" not in canonical_bytes(silent)
    assert canonical_bytes(silent) == canonical_bytes(_contract(argument_domains={}))
    assert b"argument_domains" in canonical_bytes(_domained())


def test_from_declared_reads_the_optional_seventh_key() -> None:
    declaration = dict(_declared().declaration)
    declaration["argument_domains"] = {DOMAINED_PARAMETER: {"minimum": DOMAIN_FLOOR}}
    contract = ProductRequestContract.from_declared(_declared(declaration=declaration))
    assert contract.argument_domains[DOMAINED_PARAMETER] == ArgumentDomain(
        minimum=DOMAIN_FLOOR
    )


def test_a_declaration_without_domains_still_parses() -> None:
    assert dict(ProductRequestContract.from_declared(_declared()).argument_domains) == {}


@pytest.mark.parametrize(
    "malformed",
    [[DOMAINED_PARAMETER], "optional_leaf", {DOMAINED_PARAMETER: 1}, {4: {"minimum": 1}}],
)
def test_from_declared_refuses_a_malformed_argument_domains(malformed: Any) -> None:
    declaration = dict(_declared().declaration)
    declaration["argument_domains"] = malformed
    with pytest.raises(ValueError) as raised:
        ProductRequestContract.from_declared(_declared(declaration=declaration))
    assert "argument_domains" in str(raised.value)


def test_a_domain_with_neither_end_is_refused() -> None:
    """Re-derived under `D-IMPL-264` D-03: a domain naming neither end AND no
    member set declares neither SHAPE, and *"neither shape is also invalid if
    `ArgumentDomain` is present"* — the word is still "neither"."""
    with pytest.raises(ValueError) as raised:
        ArgumentDomain()
    assert "neither" in str(raised.value)


def test_an_inverted_domain_is_refused() -> None:
    with pytest.raises(ValueError) as raised:
        ArgumentDomain(minimum=DOMAIN_CEILING, maximum=DOMAIN_FLOOR)
    assert "exceeds" in str(raised.value)


def test_a_domain_over_an_undeclared_parameter_is_refused_naming_it() -> None:
    with pytest.raises(ValueError) as raised:
        _contract(argument_domains={"never_declared": ArgumentDomain(minimum=1)})
    assert "never_declared" in str(raised.value)


def test_a_domain_over_a_parameter_without_magnitude_is_refused_naming_it() -> None:
    """A domain over a string bounds nothing; the type has no magnitude."""
    with pytest.raises(ValueError) as raised:
        _contract(argument_domains={"required_leaf": ArgumentDomain(minimum=1)})
    assert "required_leaf" in str(raised.value)
    assert "magnitude" in str(raised.value)


def test_a_domain_over_an_inert_parameter_is_refused_naming_it() -> None:
    with pytest.raises(ValueError) as raised:
        _contract(
            unsupported_arguments={INERT_PARAMETER: INERT_REASON},
            argument_domains={INERT_PARAMETER: ArgumentDomain(minimum=1)},
        )
    assert INERT_PARAMETER in str(raised.value)


def test_a_default_outside_its_own_domain_is_refused_at_declaration() -> None:
    """`D-IMPL-258` (5)'s rule one key over: the class contradicting itself
    fails where the author can fix it, never in front of a caller who omitted
    the parameter."""
    with pytest.raises(ValueError) as raised:
        _domained(defaults={DOMAINED_PARAMETER: DOMAIN_FLOOR - 1})
    assert DOMAINED_PARAMETER in str(raised.value)
    assert "outside their own domain" in str(raised.value)


def test_a_default_inside_its_domain_is_admitted() -> None:
    contract = _domained(defaults={DOMAINED_PARAMETER: DOMAIN_FLOOR})
    assert contract.defaults[DOMAINED_PARAMETER] == DOMAIN_FLOOR


def test_a_value_below_the_declared_minimum_is_refused_by_name() -> None:
    """The boundary control Dave asked for: `0` refuses."""
    verdict = refuse_request(
        request=_request(parameters={"required_leaf": "v", DOMAINED_PARAMETER: DOMAIN_FLOOR - 1}),
        declared=_domained(),
    )
    assert verdict is not None
    assert verdict.reason == "below-minimum"
    assert verdict.key == DOMAINED_PARAMETER
    assert verdict.declared_type == "integer"
    assert verdict.presented_type == "int"
    assert str(DOMAIN_FLOOR) in verdict.detail
    assert "D-IMPL-259" in verdict.detail


def test_a_value_at_the_declared_minimum_is_admitted() -> None:
    """The other half: `1` serves. Inclusive, as the ruling's *"1–100 are
    valid"* reads."""
    assert (
        refuse_request(
            request=_request(parameters={"required_leaf": "v", DOMAINED_PARAMETER: DOMAIN_FLOOR}),
            declared=_domained(),
        )
        is None
    )


def test_a_value_above_a_declared_maximum_is_refused_by_name() -> None:
    declared = _contract(
        argument_domains={
            DOMAINED_PARAMETER: ArgumentDomain(minimum=DOMAIN_FLOOR, maximum=DOMAIN_CEILING)
        }
    )
    verdict = refuse_request(
        request=_request(parameters={"required_leaf": "v", DOMAINED_PARAMETER: DOMAIN_CEILING + 1}),
        declared=declared,
    )
    assert verdict is not None
    assert verdict.reason == "above-maximum"
    assert (
        refuse_request(
            request=_request(parameters={"required_leaf": "v", DOMAINED_PARAMETER: DOMAIN_CEILING}),
            declared=declared,
        )
        is None
    )


def test_an_omitted_domained_parameter_is_not_judged_by_the_domain() -> None:
    """The domain judges what was ASKED; omission is the defaults' business
    (`D-IMPL-253` Q2), and the default is held to the domain at declaration."""
    assert (
        refuse_request(request=_request(), declared=_domained()) is None
    )


def test_a_mistyped_domained_parameter_is_the_payload_comparisons_verdict() -> None:
    """Order is load-bearing: a string where an integer was declared is
    `type-mismatch`, never a magnitude verdict about a value with none."""
    verdict = refuse_request(
        request=_request(parameters={"required_leaf": "v", DOMAINED_PARAMETER: "zero"}),
        declared=_domained(),
    )
    assert verdict is not None
    assert verdict.reason == "type-mismatch"


def test_the_domain_step_is_deterministic_over_domained_names() -> None:
    """Two offenders, one verdict, the same one on every run: sorted order."""
    arguments = _arguments()
    second = SkillArgumentProperty(type="number", description="a second number")
    schema = SkillArgumentSchema(
        properties={**dict(arguments.properties), "another": second},
        required=arguments.required,
    )
    declared = _contract(
        arguments=schema,
        argument_domains={
            DOMAINED_PARAMETER: ArgumentDomain(minimum=DOMAIN_FLOOR),
            "another": ArgumentDomain(minimum=DOMAIN_FLOOR),
        },
    )
    verdicts = {
        refuse_request(
            request=_request(
                parameters={"required_leaf": "v", DOMAINED_PARAMETER: 0, "another": 0}
            ),
            declared=declared,
        ).key  # type: ignore[union-attr]
        for _ in range(5)
    }
    assert verdicts == {"another"}


# ---------------------------------------------------------------------------
# The enumerated shape — a domain is numeric bounds OR a closed member set
# (`D-IMPL-264` D-03/D-04/D-06; plan 24.7-01).
# ---------------------------------------------------------------------------
# Dave, 2026-09-05 (Q3): *"Exactly one domain shape: numeric bounds or
# enumerated values. Non-empty, duplicate-free, and any declared default must
# be inside the domain. Neither shape is also invalid if `ArgumentDomain` is
# present."* (Q4): *"Exact canonical match. No trimming, case folding,
# aliases, or silent substitution."* (Q6): *"Any supported primitive type,
# with homogeneous members matching the declared property type."* The
# members below are the fixture's, never the SDK's (CINV-01).


def test_an_enumerated_domain_constructs_and_round_trips() -> None:
    domain = ArgumentDomain(members=("alpha", "beta"))
    assert domain.members == ("alpha", "beta")
    assert domain.minimum is None and domain.maximum is None
    assert ArgumentDomain.model_validate_json(domain.model_dump_json()) == domain


def test_the_enumerated_shape_is_silent_at_none_in_the_canonical_bytes() -> None:
    """`D-IMPL-243`, criterion 19: a numeric domain written before the member
    set existed canonicalizes byte-for-byte as it did, so no committed request
    contract's content address moves."""
    from ccf.contracts.canonical import canonical_bytes

    assert b"members" not in canonical_bytes(ArgumentDomain(minimum=DOMAIN_FLOOR))
    assert b"members" in canonical_bytes(ArgumentDomain(members=("alpha",)))


def test_a_domain_declaring_both_shapes_is_refused_naming_both() -> None:
    """D-03: numeric bounds OR a member set, never both."""
    with pytest.raises(ValueError) as raised:
        ArgumentDomain(minimum=DOMAIN_FLOOR, members=(1, 2))
    message = str(raised.value)
    assert "minimum" in message
    assert "members" in message
    assert "D-IMPL-264" in message


def test_an_empty_enumerated_domain_is_refused() -> None:
    """D-03: *"Non-empty"* — a set no value can satisfy is a key with nothing
    under it, the same defect as a domain naming neither end."""
    with pytest.raises(ValueError) as raised:
        ArgumentDomain(members=())
    assert "empty" in str(raised.value)


@pytest.mark.parametrize(
    "members, named",
    [
        (("alpha", "alpha"), "'alpha'"),
        ((1, Decimal("1")), "1"),
    ],
)
def test_a_duplicate_member_is_refused_naming_it(members: tuple[Any, ...], named: str) -> None:
    """D-03: *"duplicate-free"* — judged by the membership rule itself, so
    `1` and `Decimal("1")` ARE the same member while `1` and `True` are not."""
    with pytest.raises(ValueError) as raised:
        ArgumentDomain(members=members)
    message = str(raised.value)
    assert "duplicate" in message
    assert named in message


@pytest.mark.parametrize(
    "members",
    [("alpha", 1), (1, True), (True, "alpha"), ("alpha", Decimal("1"))],
)
def test_a_heterogeneous_member_set_is_refused_naming_the_classes(
    members: tuple[Any, ...],
) -> None:
    """D-06: *"homogeneous members"* — one class per set, `bool` its own."""
    with pytest.raises(ValueError) as raised:
        ArgumentDomain(members=members)
    message = str(raised.value)
    assert "homogeneous" in message or "heterogeneous" in message
    assert "D-IMPL-264" in message


def test_a_numeric_member_set_may_mix_int_and_decimal() -> None:
    """`int` and `Decimal` are one numeric class to this contract, on
    `_as_decimal`'s reading; `bool` is not (checked first)."""
    domain = ArgumentDomain(members=(1, Decimal("1.5")))
    assert domain.members == (1, Decimal("1.5"))


def test_a_non_finite_numeric_member_is_refused() -> None:
    """The numeric shape's own finiteness rule, carried to the member set: a
    member nothing can equal is a member nobody declared."""
    with pytest.raises(ValueError) as raised:
        ArgumentDomain(members=(Decimal("NaN"),))
    assert "finite" in str(raised.value)


@pytest.mark.parametrize(
    "presented, member",
    [("AB", "ab"), (" ab", "ab"), (True, 1), ("1", 1), (1, True), ("ab", "ab ")],
)
def test_membership_is_exact_typed_equality(presented: Any, member: Any) -> None:
    """D-04, criterion 4: no case fold, no trim, no `True == 1`, no `"1" == 1`.

    Each pair is one thing a lenient comparison would admit. The three
    executed sabotage controls (plan 24.7-01 SUMMARY) plant `.casefold()`,
    `.strip()` and an untyped `==` in turn and watch this test red.
    """
    assert ArgumentDomain(members=(member,)).refuses(presented) == "not-in-domain"


@pytest.mark.parametrize(
    "presented, members",
    [
        ("ab", ("ab",)),
        (1, (1, 2)),
        (Decimal("2"), (1, 2)),
        (2, (Decimal("1"), Decimal("2.0"))),
        (True, (True,)),
        (False, (True, False)),
    ],
)
def test_a_member_is_admitted_by_exact_equality(
    presented: Any, members: tuple[Any, ...]
) -> None:
    """The other half: exact equality within one class admits, and the numeric
    class compares by value (`Decimal("2") == 2`) rather than by Python type."""
    assert ArgumentDomain(members=members).refuses(presented) is None


def test_a_numeric_bounds_domain_judges_exactly_as_before() -> None:
    """The widened `refuses(value: object)` keeps the two-end judgment for the
    numeric shape, and says nothing about a value with no magnitude (the
    payload comparison names that one — `type-mismatch` wins by order)."""
    domain = ArgumentDomain(minimum=DOMAIN_FLOOR, maximum=DOMAIN_CEILING)
    assert domain.refuses(DOMAIN_FLOOR - 1) == "below-minimum"
    assert domain.refuses(DOMAIN_CEILING + 1) == "above-maximum"
    assert domain.refuses(DOMAIN_FLOOR) is None
    assert domain.refuses(Decimal(DOMAIN_CEILING)) is None
    assert domain.refuses("zero") is None
    assert domain.refuses(True) is None


# ---------------------------------------------------------------------------
# `not-in-domain` through the contract validator, the domain step and the
# request-conformity order (`D-IMPL-264` D-03/D-05/D-06; plan 24.7-01 Task 2).
# ---------------------------------------------------------------------------
# Dave (Q5): *"New `not-in-domain` reason. Wrong type and valid type/wrong
# value are materially different failures. The presented value can be named;
# disclosure controls whether the allowed set is exposed."* The members are
# the fixture's, never the SDK's (CINV-01).

ENUMERATED_PARAMETER = "required_leaf"
ENUMERATED_MEMBERS = ("alpha", "beta")


def _enumerated(**overrides: Any) -> ProductRequestContract:
    fields: dict[str, Any] = {
        "argument_domains": {
            ENUMERATED_PARAMETER: ArgumentDomain(members=ENUMERATED_MEMBERS)
        }
    }
    fields.update(overrides)
    return _contract(**fields)


def _typed_arguments() -> SkillArgumentSchema:
    """The fixture surface plus a `number` and a `boolean` leaf, so every
    primitive type `D-IMPL-264` D-06 admits has a declared parameter."""
    arguments = _arguments()
    return SkillArgumentSchema(
        properties={
            **dict(arguments.properties),
            "numeric_leaf": SkillArgumentProperty(type="number", description="a number"),
            "flag_leaf": SkillArgumentProperty(type="boolean", description="a flag"),
        },
        required=arguments.required,
    )


def test_an_enumerated_domain_over_a_string_parameter_is_admitted() -> None:
    """D-06: the sibling of the magnitude refusal — an enumerated shape over a
    string is exactly what the shape is for."""
    contract = _enumerated()
    assert contract.argument_domains[ENUMERATED_PARAMETER].members == ENUMERATED_MEMBERS
    assert (
        ProductRequestContract.model_validate_json(contract.model_dump_json())
        == contract
    )


@pytest.mark.parametrize(
    "name, members",
    [
        ("required_leaf", ("alpha",)),
        ("optional_leaf", (1, 2)),
        ("numeric_leaf", (1, Decimal("1.5"))),
        ("flag_leaf", (True, False)),
    ],
)
def test_an_enumerated_domain_is_admitted_over_every_primitive_type(
    name: str, members: tuple[Any, ...]
) -> None:
    """Criterion 5: string, integer, number, boolean — *"don't unnecessarily
    make this string-specific"*."""
    contract = _contract(
        arguments=_typed_arguments(),
        argument_domains={name: ArgumentDomain(members=members)},
    )
    assert contract.argument_domains[name].members == members


def test_numeric_bounds_over_a_string_parameter_stay_refused_as_unmeasurable() -> None:
    """Criterion 5's other half: relaxing `unmeasurable` for the enumerated
    shape must not relax it for the numeric one."""
    with pytest.raises(ValueError) as raised:
        _contract(argument_domains={"required_leaf": ArgumentDomain(minimum=1)})
    assert "required_leaf" in str(raised.value)
    assert "magnitude" in str(raised.value)


@pytest.mark.parametrize(
    "name, members, declared",
    [
        ("optional_leaf", ("alpha",), "integer"),
        ("required_leaf", (1,), "string"),
        ("optional_leaf", (Decimal("1.5"),), "integer"),
        ("flag_leaf", (1, 0), "boolean"),
        ("numeric_leaf", (True,), "number"),
        ("nested", ("alpha",), "object"),
    ],
)
def test_a_mistyped_enumerated_domain_is_refused_naming_the_parameter(
    name: str, members: tuple[Any, ...], declared: str
) -> None:
    """D-06: *"homogeneous members matching the declared property type"* —
    a member set whose class is not the property's is refused at contract
    construction, naming the parameter and the declared type (criterion 1)."""
    with pytest.raises(ValueError) as raised:
        _contract(
            arguments=_typed_arguments(),
            argument_domains={name: ArgumentDomain(members=members)},
        )
    message = str(raised.value)
    # The fragment the `mistyped` list renders for THIS parameter, so the
    # assertion cannot be satisfied by the sentence's other clauses (which
    # name every offender class, and the words "integer" and "number", on
    # every refusal).
    assert f"{name} declares {declared} but enumerates" in message
    assert "mistyped" in message


def test_a_default_outside_an_enumerated_domain_is_refused_at_declaration() -> None:
    """Criterion 2: the existing default-respects-domain validator, extended to
    membership — the class contradicting itself fails where the author can
    fix it, naming the parameter."""
    with pytest.raises(ValueError) as raised:
        _enumerated(defaults={ENUMERATED_PARAMETER: "gamma"})
    # The `contradicted` list, with this parameter IN it — the sentence
    # carries the fragment on every refusal, so the bare substring would pass
    # against an `unmeasurable` refusal of the same contract.
    assert (
        f"['{ENUMERATED_PARAMETER}'] carry a declared default outside their own domain"
        in str(raised.value)
    )


def test_a_default_inside_an_enumerated_domain_is_admitted() -> None:
    contract = _enumerated(defaults={ENUMERATED_PARAMETER: ENUMERATED_MEMBERS[0]})
    assert contract.defaults[ENUMERATED_PARAMETER] == ENUMERATED_MEMBERS[0]


def test_from_declared_reads_an_enumerated_domain() -> None:
    declaration = dict(_declared().declaration)
    declaration["argument_domains"] = {
        ENUMERATED_PARAMETER: {"members": list(ENUMERATED_MEMBERS)}
    }
    contract = ProductRequestContract.from_declared(_declared(declaration=declaration))
    assert contract.argument_domains[ENUMERATED_PARAMETER] == ArgumentDomain(
        members=ENUMERATED_MEMBERS
    )


def test_a_value_outside_an_enumerated_domain_is_refused_as_not_in_domain() -> None:
    """Criterion 3: returned as data by the domain step, naming the key and the
    presented value; the allowed set rides in `detail` (D-05)."""
    verdict = refuse_request(
        request=_request(parameters={ENUMERATED_PARAMETER: "gamma"}),
        declared=_enumerated(),
    )
    assert verdict is not None
    assert verdict.reason == "not-in-domain"
    assert verdict.key == ENUMERATED_PARAMETER
    assert verdict.declared_type == "string"
    assert verdict.presented_type == "str"
    assert "gamma" in verdict.detail
    for member in ENUMERATED_MEMBERS:
        assert member in verdict.detail
    assert "D-IMPL-264" in verdict.detail
    assert verdict.declared_keys == frozenset(_arguments().properties)
    assert verdict.presented_keys == frozenset({ENUMERATED_PARAMETER})


def test_a_mistyped_enumerated_parameter_is_still_type_mismatch() -> None:
    """D-05: *"wrong type and valid type/wrong value are materially different
    failures"* — the payload comparison still wins by order."""
    verdict = refuse_request(
        request=_request(parameters={ENUMERATED_PARAMETER: 1}),
        declared=_enumerated(),
    )
    assert verdict is not None
    assert verdict.reason == "type-mismatch"


def test_a_member_of_an_enumerated_domain_is_admitted_end_to_end() -> None:
    assert (
        refuse_request(
            request=_request(parameters={ENUMERATED_PARAMETER: ENUMERATED_MEMBERS[1]}),
            declared=_enumerated(),
        )
        is None
    )


def test_an_earlier_step_wins_over_the_enumerated_domain_step() -> None:
    """The order is unchanged and the domain step is still LAST: a request the
    address or tier step refuses never reaches membership."""
    inert = _enumerated(unsupported_arguments={INERT_PARAMETER: INERT_REASON})
    tier = refuse_request(
        request=_request(
            parameters={ENUMERATED_PARAMETER: "gamma", INERT_PARAMETER: "x"}
        ),
        declared=inert,
    )
    assert tier is not None and tier.reason == "not-supported-at-tier"
    address = refuse_request(
        request=_request(
            schema_version="9.9.9", parameters={ENUMERATED_PARAMETER: "gamma"}
        ),
        declared=_enumerated(),
    )
    assert address is not None and address.reason == "class-mismatch"


def test_the_ninth_reason_names_no_runtime_module() -> None:
    """Criterion 7: `runtime/` is untouched by the new reason — the door maps
    by CLASS (`ProductRequestViolation` -> 400), never by reason token."""
    runtime = REQUEST_MODULE.parent.parent.parent.parent / "runtime"
    hits = [
        path
        for path in runtime.rglob("*.py")
        if "not-in-domain" in path.read_text(encoding="utf-8")
    ]
    assert hits == []
