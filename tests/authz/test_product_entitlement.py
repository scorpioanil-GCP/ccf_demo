"""The product-entitlement artifact: lane, closure, entitlement, tenancy.

Named per property defended, on the shape ``tests/peering/test_trust_policy.py``
already proves for the A2A boundary.

Two of these exist because a weaker suite would pass against a broken
implementation:

* the **field-enumeration** test makes "this contract cannot express a bypass"
  a claim the suite enforces rather than one the docstring asserts — a
  docstring cannot fail when a later contributor adds ``unrestricted_principal``;
* the **two-tenant** test is the D-23 obligation: an entitlement check that is
  right with one tenant and wrong with two is the CR-01 defect class, and a
  single-tenant suite would not see it.

Principal identifiers, role names and product-class names are all fixture
vocabulary. The SDK enumerates none of them.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products import entitlement as entitlement_module
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    PrincipalNotEntitled,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    ProductEntitlementViolation,
    product_entitlement_key,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

PRINCIPAL = "analyst-4471"
OTHER_PRINCIPAL = "auditor-9902"
TENANT_ONE = "acme-bank"
TENANT_TWO = "borealis-bank"
UNGRANTED_ROLE = "chief-risk-officer"
UNGRANTED_SCHEMA = "acme-bank.some-other-product"

#: Any attribute name matching one of these would let a deployment configure
#: its way around the entitlement lookup — a principal, a class or a role
#: granted by something other than a declaration somebody wrote. Their absence
#: is the mechanism, so the absence is asserted rather than described.
FORBIDDEN_FIELD_MARKERS = (
    "bypass",
    "allow_all",
    "skip",
    "unrestricted",
    "fast_path",
    "fastpath",
    "default_grant",
    "any_",
)


def _fixture(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def _schema_name() -> str:
    schema: str = _fixture("controlplane.yaml")["product_class"]["schema_name"]
    return schema


def _role() -> str:
    role: str = _fixture("controlplane.yaml")["perspective"]["role"]
    return role


def grant(
    *,
    schema_names: frozenset[str] | None = None,
    roles: frozenset[str] | None = None,
) -> ProductEntitlementGrant:
    return ProductEntitlementGrant(
        permitted_schema_names=(
            schema_names if schema_names is not None else frozenset({_schema_name()})
        ),
        permitted_roles=(roles if roles is not None else frozenset({_role()})),
    )


def policy(
    *, tenant_id: str = TENANT_ONE, **kwargs: Any
) -> ProductEntitlementPolicy:
    return ProductEntitlementPolicy(
        tenant_id=tenant_id,
        policy_version="1.0.0",
        principals={PRINCIPAL: grant(**kwargs)},
    )


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


# --- the semver lane -------------------------------------------------------


def test_a_policy_without_a_version_lane_cannot_be_constructed() -> None:
    with pytest.raises(ValidationError):
        ProductEntitlementPolicy(  # type: ignore[call-arg]
            tenant_id=TENANT_ONE, principals={PRINCIPAL: grant()}
        )


def test_a_policy_with_a_malformed_version_lane_is_refused() -> None:
    with pytest.raises(ValidationError):
        ProductEntitlementPolicy(
            tenant_id=TENANT_ONE,
            policy_version="one",
            principals={PRINCIPAL: grant()},
        )


def test_a_policy_naming_no_principals_is_refused() -> None:
    """An empty policy is indistinguishable from a forgotten one."""
    with pytest.raises(ValidationError):
        ProductEntitlementPolicy(
            tenant_id=TENANT_ONE, policy_version="1.0.0", principals={}
        )


# --- closure ---------------------------------------------------------------


def test_an_unknown_field_on_a_policy_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductEntitlementPolicy(
            tenant_id=TENANT_ONE,
            policy_version="1.0.0",
            principals={PRINCIPAL: grant()},
            unrestricted_principal=PRINCIPAL,  # type: ignore[call-arg]
        )


def test_an_unknown_field_on_a_grant_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductEntitlementGrant(
            permitted_schema_names=frozenset(),
            permitted_roles=frozenset(),
            allow_all_schemas=True,  # type: ignore[call-arg]
        )


def test_no_field_on_the_contract_could_express_a_bypass() -> None:
    """The module's one enumeration-strength claim, made executable.

    Enforced here rather than in a docstring, because a docstring cannot fail
    when a later contributor adds ``unrestricted_principal``. The union across
    both models is deliberate: a bypass field on either one is a bypass, and
    checking only the policy would leave the grant open.
    """
    names = set(ProductEntitlementPolicy.model_fields) | set(
        ProductEntitlementGrant.model_fields
    )
    offending = [
        name
        for name in names
        if any(marker in name.lower() for marker in FORBIDDEN_FIELD_MARKERS)
    ]
    assert offending == []


def test_the_field_enumeration_scan_is_not_vacuous() -> None:
    """A marker set that matched nothing on purpose would pass forever.

    The guard the trust-policy suite's own non-vacuity argument implies: the
    scan must be reading real fields, and the predicate must be capable of
    firing.
    """
    names = set(ProductEntitlementPolicy.model_fields) | set(
        ProductEntitlementGrant.model_fields
    )
    assert {"tenant_id", "principals", "permitted_roles"} <= names
    assert any(
        marker in "unrestricted_principal" for marker in FORBIDDEN_FIELD_MARKERS
    )


# --- entitlement -----------------------------------------------------------


def test_a_principal_may_receive_only_the_classes_its_grant_lists() -> None:
    entry = policy().grant_for(principal_id=PRINCIPAL)
    entry.require_schema(schema_name=_schema_name())
    with pytest.raises(ProductEntitlementViolation):
        entry.require_schema(schema_name=UNGRANTED_SCHEMA)


def test_a_principal_may_assert_only_the_roles_its_grant_lists() -> None:
    entry = policy().grant_for(principal_id=PRINCIPAL)
    entry.require_role(role=_role())
    with pytest.raises(ProductEntitlementViolation):
        entry.require_role(role=UNGRANTED_ROLE)


def test_an_empty_grant_permits_nothing_rather_than_everything() -> None:
    """The permissive reading of an empty set is the bypass in disguise."""
    entry = ProductEntitlementGrant(
        permitted_schema_names=frozenset(), permitted_roles=frozenset()
    )
    with pytest.raises(ProductEntitlementViolation):
        entry.require_schema(schema_name=_schema_name())
    with pytest.raises(ProductEntitlementViolation):
        entry.require_role(role=_role())


def test_an_unconfigured_principal_is_refused_not_given_an_empty_grant() -> None:
    with pytest.raises(PrincipalNotEntitled):
        policy().grant_for(principal_id=OTHER_PRINCIPAL)


def test_neither_resolution_surface_returns_a_boolean() -> None:
    """A refusal a caller can read as "not sure" is not a refusal.

    Both checks return ``None`` on success, so there is no truthy/falsy value
    an admission path could branch on and mistake for a verdict.
    """
    entry = policy().grant_for(principal_id=PRINCIPAL)
    assert entry.require_schema(schema_name=_schema_name()) is None
    assert entry.require_role(role=_role()) is None


# --- the key derivation ----------------------------------------------------


def test_the_key_derivation_is_a_pure_function_of_its_argument() -> None:
    key = product_entitlement_key(tenant_id=TENANT_ONE)
    assert key == product_entitlement_key(tenant_id=TENANT_ONE)
    assert key.startswith(f"{PRODUCT_ENTITLEMENT_POLICY.class_id}/")
    assert TENANT_ONE in key


def test_two_tenants_never_share_a_control_plane_key() -> None:
    assert product_entitlement_key(
        tenant_id=TENANT_ONE
    ) != product_entitlement_key(tenant_id=TENANT_TWO)


def test_the_module_source_holds_no_deployment_vocabulary() -> None:
    """CINV-01, asserted against the module rather than described in it.

    Every identifier this suite uses is fixture vocabulary. None of it may
    appear in ``/src``: a tenant, a principal, a role or a product-class name
    the SDK chose is one no examiner could trace to a decision anyone made.
    """
    source = inspect.getsource(entitlement_module)
    for value in (
        TENANT_ONE,
        TENANT_TWO,
        PRINCIPAL,
        OTHER_PRINCIPAL,
        UNGRANTED_ROLE,
        UNGRANTED_SCHEMA,
        _schema_name(),
        _role(),
    ):
        assert value not in source, value


# --- registration ----------------------------------------------------------


def test_registering_a_bare_mapping_under_the_class_is_refused(
    registry: ControlPlaneRegistry,
) -> None:
    """Registering the wrong thing must be a detectable error, not a plausible
    one — the whole argument for a typed artifact class."""
    key = product_entitlement_key(tenant_id=TENANT_ONE)
    with pytest.raises(TypeError):
        registry.register_typed(key, {"principals": {}}, PRODUCT_ENTITLEMENT_POLICY)


def test_a_registered_policy_resolves_by_pinned_key_and_version(
    registry: ControlPlaneRegistry,
) -> None:
    key = product_entitlement_key(tenant_id=TENANT_ONE)
    registered = policy()
    version = registry.register_typed(key, registered, PRODUCT_ENTITLEMENT_POLICY)
    assert registry.resolve(key, version) == registered


def test_a_policy_is_an_auditable_canonically_serializable_value() -> None:
    registered = policy()
    assert isinstance(registered, CCFContract)
    assert json.loads(registered.model_dump_json())["tenant_id"] == TENANT_ONE


# --- the D-23 two-tenant case ----------------------------------------------


def test_two_tenant_policies_hold_two_content_addresses() -> None:
    """The tenant is *in the content*, so there is no shared object to leak
    through — the property the field placement buys, asserted rather than
    argued."""
    one = policy(tenant_id=TENANT_ONE)
    two = policy(tenant_id=TENANT_TWO)
    assert content_hash(one) != content_hash(two)


def test_two_tenant_a_principal_entitled_under_one_is_not_under_the_other() -> None:
    """The same principal, granted different classes per tenant, stays
    separated — and neither grant leaks into the other's lookup."""
    one = policy(tenant_id=TENANT_ONE, schema_names=frozenset({_schema_name()}))
    two = policy(
        tenant_id=TENANT_TWO, schema_names=frozenset({UNGRANTED_SCHEMA})
    )
    one.grant_for(principal_id=PRINCIPAL).require_schema(
        schema_name=_schema_name()
    )
    with pytest.raises(ProductEntitlementViolation):
        two.grant_for(principal_id=PRINCIPAL).require_schema(
            schema_name=_schema_name()
        )


def test_two_tenant_policies_resolve_independently(
    registry: ControlPlaneRegistry,
) -> None:
    """One tenant's grant to a principal must not resolve for another tenant."""
    one = policy(tenant_id=TENANT_ONE, schema_names=frozenset({_schema_name()}))
    two = policy(
        tenant_id=TENANT_TWO, schema_names=frozenset({UNGRANTED_SCHEMA})
    )
    key_one = product_entitlement_key(tenant_id=TENANT_ONE)
    key_two = product_entitlement_key(tenant_id=TENANT_TWO)
    version_one = registry.register_typed(key_one, one, PRODUCT_ENTITLEMENT_POLICY)
    version_two = registry.register_typed(key_two, two, PRODUCT_ENTITLEMENT_POLICY)

    assert key_one != key_two
    assert version_one != version_two
    resolved_one = registry.resolve(key_one, version_one)
    assert isinstance(resolved_one, ProductEntitlementPolicy)
    assert resolved_one.tenant_id == TENANT_ONE
    assert resolved_one.grant_for(
        principal_id=PRINCIPAL
    ).permitted_schema_names == frozenset({_schema_name()})


def test_a_second_tenant_never_entitles_an_unconfigured_principal(
    registry: ControlPlaneRegistry,
) -> None:
    """The refusal survives the two-tenant case, which is where a lookup that
    fell back to "any registered policy" would quietly start working."""
    key_two = product_entitlement_key(tenant_id=TENANT_TWO)
    two = policy(tenant_id=TENANT_TWO)
    registry.register_typed(key_two, two, PRODUCT_ENTITLEMENT_POLICY)
    with pytest.raises(PrincipalNotEntitled):
        two.grant_for(principal_id=OTHER_PRINCIPAL)
